import asyncio
import os
from typing import List

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_404_NOT_FOUND

from src.config import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    NAME,
    PASSWORD,
    SECRET,
    UPLOAD_FOLDER,
    logger,
    manifest,
    save_photo_executor,
    templates
)
from src.utils import get_unique_filename, save_photo

logger.info("Launching app...")

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=SECRET)

logger.info("Middleware has been added.")
logger.info("Setting up endpoints...")


# ---------- ENDPOINTS ----------


def require_login(request: Request):
    """Check login session. Redirect to login page if session DNE."""

    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=302, detail="Redirect", headers={"Location": "/login"}
        )
    return user


@app.on_event("shutdown")
def shutdown_event():
    """Safely shut down app."""

    logger.info("Shutting down app...")
    save_photo_executor.shutdown(wait=True)
    logger.info("Closed save-photo executor.")
    logger.info("App shut down.")


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login_action(request: Request):
    """Submit login information."""

    form = await request.form()
    un = form.get("name")
    pw = form.get("password")

    # check creds and remember user
    if pw == PASSWORD:
        request.session["user"] = un
        logger.info(f"User '{un}' has logged into the app.")
        return RedirectResponse("/", status_code=302)

    logger.warning(f"Invalid login attempt by user '{un}'.")

    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Invalid username or password"}
    )


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user: str = Depends(require_login)):
    """Home page."""
    return templates.TemplateResponse("index.html", {"request": request, "name": NAME})


@app.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request, user: str = Depends(require_login)):
    """Upload page."""
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/upload")
async def upload_photos(
    request: Request,
    files: List[UploadFile] = File(...),
    user: str = Depends(require_login),
):
    """Upload multiple photos."""

    success_count = 0
    error_count = 0

    try:
        for file in files:
            filename = file.filename or ""
            ext = os.path.splitext(filename)[1].lower()

            if (
                ext not in ALLOWED_EXTENSIONS
                or file.content_type not in ALLOWED_MIME_TYPES
            ):
                logger.warning(
                    f"Rejected file '{file.filename}': unsupported file type ({file.content_type})."
                )
                error_count += 1
                continue

            # get unique + safe filename
            unique_filename = get_unique_filename(manifest, file.filename)
            file_location = os.path.join(UPLOAD_FOLDER, unique_filename)

            await asyncio.get_running_loop().run_in_executor(
                save_photo_executor, save_photo, file_location, file, user
            )

            manifest.add(unique_filename)
            logger.info(f"File '{unique_filename}' uploaded by user '{user}'.")
            success_count += 1

        if success_count == 0:
            return templates.TemplateResponse(
                "upload.html",
                {
                    "request": request,
                    "success": False,
                    "error": "No valid images were uploaded.",
                },
            )

        logger.info(f"Uploaded {success_count} files and rejected {error_count} files.")

        return templates.TemplateResponse(
            "upload.html", {"request": request, "success": True}
        )

    except Exception:
        logger.error("Failed to upload files.", exc_info=True)

        return templates.TemplateResponse(
            "upload.html", {"request": request, "success": False, "error": True}
        )


@app.get("/photos", response_class=HTMLResponse)
async def view_photos(request: Request, user: str = Depends(require_login)):
    """Photo gallery page."""

    try:

        return templates.TemplateResponse(
            "gallery.html", {"request": request, "photos": manifest}
        )

    except Exception:
        logger.error("Failed to fetch photos.", exc_info=True)

        return templates.TemplateResponse(
            "gallery.html", {"request": request, "success": False, "error": True}
        )


@app.get("/photos/{filename}", response_class=FileResponse)
async def serve_photo(
    filename: str, request: Request, user: str = Depends(require_login)
):
    """Serve photos for the gallery."""

    try:
        # ensure the file is inside the photos folder
        if filename not in manifest:
            logger.warning(f"User '{user}' requested invalid file: {filename}")
            return HTMLResponse("File not found.", status_code=HTTP_404_NOT_FOUND)

        file_path = f"{UPLOAD_FOLDER}/{filename}"

        return FileResponse(file_path)

    except Exception:
        logger.error(f"Failed to fetch photo '{filename}'.", exc_info=True)

        return templates.TemplateResponse(
            "gallery.html", {"request": request, "success": False, "error": True}
        )


@app.get("/veggietales")
async def veggies(user: str = Depends(require_login)):
    """Oh, where is my hairbrush?"""
    return RedirectResponse(url="https://www.youtube.com/watch?v=i3fL5e4ECYs")


logger.info("App is running.")
logger.info(f"Current manifest: {manifest}")
