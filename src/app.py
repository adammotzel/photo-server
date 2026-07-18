import asyncio
import os
import uuid
from contextlib import asynccontextmanager

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
    templates,
)
from src.db import (
    create_user,
    get_user_by_id,
    get_user_by_username,
    pool,
    write_prediction,
)
from src.logger import listener, logger
from src.model import inference
from src.utils import save_photo


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown control."""

    app.state.shutting_down = False
    listener.start()
    pool.open()

    yield

    app.state.shutting_down = True
    pool.close()

    logger.info("Shutdown complete.")
    listener.stop()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET,  # ty: ignore[invalid-argument-type]
)


async def _process_upload(file: UploadFile, username: str) -> bool:
    """
    Validate, classify, and save a single uploaded photo. Returns True on success.

    Parameters
    ----------
    file : UploadFile
        File to upload.
    username : str
        Username of the uploader.

    Returns
    -------
    bool
        If the upload was successful.
    """

    try:
        filename = file.filename or ""
        ext = os.path.splitext(filename)[-1].lower()

        if ext not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_MIME_TYPES:
            logger.warning(
                f"Rejected file '{file.filename}': unsupported file type ({file.content_type})."
            )
            return False

        # get unique + safe filename
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_location = os.path.join(UPLOAD_FOLDER, unique_filename)

        contents = await file.read()
        content_type = file.content_type

        # check for dawgs
        predicted_label, confidence = await run_in_threadpool(
            inference,
            contents,
        )

        if predicted_label != "dog":
            logger.warning(
                f"Image rejected. Expected a dog, received '{predicted_label}'"
            )
            await run_in_threadpool(
                write_prediction,
                None,
                filename,
                predicted_label,
                confidence,
                False,
                username,
            )
            return False

        photo_id = await run_in_threadpool(
            save_photo,
            file_location,
            contents,
            unique_filename,
            content_type,
            username,
        )
        await run_in_threadpool(
            write_prediction,
            photo_id,
            filename,
            predicted_label,
            confidence,
            True,
            username,
        )
        return True
    except Exception:
        logger.error("A file uploaded failed.", exc_info=True)
        return False


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
    hashed = await run_in_threadpool(
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
    files: list[UploadFile] = File(...),
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

    results = await asyncio.gather(
        *(_process_upload(file, user["username"]) for file in files)
    )

    success_count = sum(results)
    error_count = len(results) - success_count

    # everything failed
    if success_count == 0:
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "success": False,
                "partial": False,
                "error": "No valid images were uploaded.",
            },
        )

    # at least one image was uploaded
    elif error_count > 0:
        msg = f"Accepted {success_count} image(s), rejected {error_count} image(s)."
        logger.info(msg)

        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "success": False,
                "partial": True,
                "error": msg,
            },
        )

    # all images were uploaded
    else:
        logger.info(f"Uploaded {success_count} files.")

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

        return FileResponse(
            file_path,
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

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
