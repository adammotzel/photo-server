import os
import uuid
from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from src.auth import hash_password, verify_password
from src.config import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    NAME,
    SECRET,
    UPLOAD_FOLDER,
    logger,
    templates,
)
from src.db import create_user, get_user_by_id, get_user_by_username
from src.utils import save_photo

logger.info("Launching app...")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown control."""

    app.state.shutting_down = False

    logger.info("App startup complete.")

    yield

    logger.info("Shutdown initiated.")

    app.state.shutting_down = True

    logger.info("Shutdown complete.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET,  # ty: ignore[invalid-argument-type]
)

logger.info("Middleware has been added.")
logger.info("Setting up endpoints...")


# ---------- ENDPOINTS ----------


async def require_login(request: Request):
    """Check login session. Redirect to login page if session DNE."""

    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=302,
            headers={"Location": "/login"},
        )

    user = await run_in_threadpool(
        get_user_by_id,
        user_id,
    )
    return user


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "registered": request.query_params.get("registered")},
    )


@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    """Serve Registration form."""
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register(request: Request):
    """Request to register a new user."""

    form = await request.form()
    username = form.get("name")
    password = form.get("password")

    logger.info("Request received to register new user.")

    if not username or not password:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Missing username or password"},
        )

    logger.info("Checking if supplied username exists...")

    username_str = str(username)
    existing = await run_in_threadpool(
        get_user_by_username,
        username_str,
    )

    if existing:
        logger.warning("Supplied username already exists. Rejecting registration.")
        return templates.TemplateResponse(
            "register.html", {"request": request, "error": "Username already exists"}
        )

    logger.info("Creating new user...")

    # use separate ProcessPoolExecutor???
    hashed = run_in_threadpool(
        hash_password,
        str(password),
    )
    await run_in_threadpool(
        create_user,
        username_str,
        str(hashed),
    )

    logger.info("New user created successfully.")

    # optional: clear session just in case
    request.session.clear()

    return RedirectResponse("/login?registered=1", status_code=302)


@app.post("/login")
async def login_action(request: Request):
    """Submit login information."""

    form = await request.form()
    username = form.get("name")
    password = form.get("password")

    logger.info("Login request received. Validating credentials...")

    if not username or not password:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Invalid username or password"}
        )

    user = await run_in_threadpool(
        get_user_by_username,
        str(username),
    )

    if not user:
        logger.warning("Invalid login attempt. Rejecting login.")
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Invalid username or password"}
        )

    verify = await run_in_threadpool(
        verify_password,
        str(password),
        user["password_hash"],
    )

    if not verify:
        logger.warning("Invalid login attempt. Rejecting login.")
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Invalid username or password"}
        )

    request.session["user_id"] = user["id"]
    request.session["username"] = user["username"]

    logger.info("Login request accepted.")

    return RedirectResponse("/", status_code=302)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user: dict = Depends(require_login)):
    """Serve the Home page."""
    return templates.TemplateResponse("index.html", {"request": request, "name": NAME})


@app.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request, user: dict = Depends(require_login)):
    """Serve the Upload page."""
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/upload")
async def upload_photos(
    request: Request,
    files: List[UploadFile] = File(...),
    user: dict = Depends(require_login),
):
    """Upload multiple photos."""

    logger.info(f"Request received to upload {len(files)} files.")

    if request.app.state.shutting_down:
        logger.warning("App is shutting down; rejecting upload attempt.")
        raise HTTPException(
            status_code=503,
            detail="Server is shutting down. Uploads temporarily unavailable.",
        )

    logger.info("Uploading files...")

    success_count = 0
    error_count = 0

    for file in files:
        try:
            filename = file.filename or ""
            ext = os.path.splitext(filename)[-1].lower()

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
            unique_filename = f"{uuid.uuid4()}{ext}"
            file_location = os.path.join(UPLOAD_FOLDER, unique_filename)

            contents = await file.read()
            content_type = file.content_type

            await run_in_threadpool(
                save_photo,
                file_location,
                contents,
                unique_filename,
                content_type,
                user["username"],
            )

            success_count += 1
        except Exception:
            logger.error("A file uploaded failed.", exc_info=True)
            error_count += 1

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


@app.get("/photos", response_class=HTMLResponse)
async def view_photos(request: Request, user: dict = Depends(require_login)):
    """Photo gallery page."""

    logger.info("Request received to view photo gallery.")

    manifest = await run_in_threadpool(
        os.listdir,
        "src/photos",
    )
    manifest = [
        file
        for file in manifest
        if isinstance(file, str) and file.lower().endswith(ALLOWED_EXTENSIONS)
    ]

    logger.info(f"Surfacing {len(manifest)} photos for the gallery...")

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
    filename: str, request: Request, user: dict = Depends(require_login)
):
    """Serve photos for the gallery."""

    try:
        file_path = os.path.join(UPLOAD_FOLDER, os.path.basename(filename))

        return FileResponse(file_path)

    except Exception:
        logger.error(f"Failed to fetch photo '{filename}'.", exc_info=True)

        return templates.TemplateResponse(
            "gallery.html", {"request": request, "success": False, "error": True}
        )


@app.get("/veggietales")
async def veggies(user: dict = Depends(require_login)):
    """Oh, where is my hairbrush?"""
    logger.warning("No hair for my hairbrush!")
    return RedirectResponse(url="https://www.youtube.com/watch?v=i3fL5e4ECYs")
