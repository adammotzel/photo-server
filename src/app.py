import os
import traceback
import asyncio

from fastapi import (
    FastAPI, 
    Request, 
    UploadFile, 
    File,
    Depends,
    HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_404_NOT_FOUND

from src.utils import get_unique_filename, save_photo
from src.config import (
    logger,
    templates,
    save_photo_executor,
    manifest,
    USERNAMES,
    PASSWORD,
    SECRET,
    NAME,
    UPLOAD_FOLDER,
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES
)


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
        raise HTTPException(status_code=302, detail="Redirect", headers={"Location": "/login"})
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
    un = form.get("username")
    pw = form.get("password")

    # check creds
    if un in USERNAMES and pw == PASSWORD:
        request.session["user"] = un
        logger.info(f"User '{un}' has logged into the app.")
        return RedirectResponse("/", status_code=302)
    
    logger.warning(f"Invalid login attempt by user '{un}'.")
    
    return templates.TemplateResponse(
        "login.html", 
        {
            "request": request,
            "error": "Invalid username or password"
        }
    )


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user: str = Depends(require_login)):
    """Home page."""
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request,
            "name": NAME
        }
    )


@app.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request, user: str = Depends(require_login)):
    """Upload page."""
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/upload")
async def upload_photo(
    request: Request, 
    file: UploadFile = File(...), 
    user: str = Depends(require_login)
):
    """Upload photo action."""

    try:

        # check file type
        filename = file.filename or ""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_MIME_TYPES:
            logger.warning(
                f"Rejected file '{file.filename}': unsupported file type ({file.content_type})."
            )

            return templates.TemplateResponse(
                "upload.html", {
                    "request": request,
                    "success": False,
                    "error": "Unsupported file type. Please upload a valid image file."
                }
            )
        
        # sanitize filename, and ensure filename is unique
        unique_filename = get_unique_filename(manifest, file.filename)
        file_location = os.path.join(UPLOAD_FOLDER, unique_filename)

        # save to /photos directory
        await asyncio.get_running_loop().run_in_executor(
            save_photo_executor, 
            save_photo, 
            file_location, 
            file
        )

        # add new file to manifest
        manifest.add(unique_filename)
        
        logger.info(f"File '{unique_filename}' uploaded to photos.")

        return templates.TemplateResponse(
            "upload.html", 
            {
                "request": request,
                "success": True
            }
        )
    
    except Exception:
        
        error_trace = traceback.format_exc()
        logger.error(f"Failed to upload file '{unique_filename}' to photos.")
        logger.error(f"Error: {error_trace}")

        return templates.TemplateResponse(
            "upload.html", 
            {
                "request": request,
                "success": False,
                "error": True
            }
        )


@app.get("/photos", response_class=HTMLResponse)
async def view_photos(request: Request, user: str = Depends(require_login)):
    """Photo gallery page."""

    try:

        return templates.TemplateResponse(
            "gallery.html", 
            {
                "request": request,
                "photos": manifest
            }
        )
    
    except Exception:
        error_trace = traceback.format_exc()
        logger.error(f"Failed to fetch photos.")
        logger.error(f"Error: {error_trace}")

        return templates.TemplateResponse(
            "gallery.html", 
            {
                "request": request,
                "success": False,
                "error": True
            }
        )
    

@app.get("/photos/{filename}", response_class=FileResponse)
async def serve_photo(
    filename: str, 
    request: Request, 
    user: str = Depends(require_login)
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
        error_trace = traceback.format_exc()
        logger.error(f"Failed to fetch photo '{filename}'.")
        logger.error(f"Error: {error_trace}")

        return templates.TemplateResponse(
            "gallery.html", 
            {
                "request": request,
                "success": False,
                "error": True
            }
        )


@app.get("/veggietales")
async def veggies(user: str = Depends(require_login)):
    """Oh, where is my hairbrush?"""
    return RedirectResponse(url="https://www.youtube.com/watch?v=i3fL5e4ECYs")


logger.info("App is running.")
logger.info(f"Current manifest: {manifest}")
