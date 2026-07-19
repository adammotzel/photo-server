import asyncio
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from src.config import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    NAME,
    UPLOAD_FOLDER,
    templates,
)
from src.db import pool, write_prediction
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


async def _process_upload(file: UploadFile, uploader_ip: str) -> bool:
    """
    Validate, classify, and save a single uploaded photo. Returns True on success.

    Parameters
    ----------
    file : UploadFile
        File to upload.
    uploader_ip : str
        LAN IP address of the uploading device.

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
                f"Rejected file '{filename}': unsupported file type ({file.content_type})."
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
                f"Image '{filename}' rejected. Expected a dog, received '{predicted_label}'"
            )
            await run_in_threadpool(
                write_prediction,
                None,
                filename,
                predicted_label,
                confidence,
                False,
                uploader_ip,
            )
            return False

        photo_id = await run_in_threadpool(
            save_photo,
            file_location,
            contents,
            unique_filename,
            content_type,
            uploader_ip,
        )
        await run_in_threadpool(
            write_prediction,
            photo_id,
            filename,
            predicted_label,
            confidence,
            True,
            uploader_ip,
        )
        return True
    except Exception:
        logger.error("A file uploaded failed.", exc_info=True)
        return False


# ---------- ENDPOINTS ----------


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the Home page."""
    return templates.TemplateResponse("index.html", {"request": request, "name": NAME})


@app.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request):
    """Serve the Upload page."""
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/upload")
async def upload_photos(
    request: Request,
    files: list[UploadFile] = File(...),
):
    """Upload multiple photos."""

    uploader_ip = request.client.host if request.client else "unknown"

    logger.info(f"Request received to upload {len(files)} by {uploader_ip}.")

    if request.app.state.shutting_down:
        logger.warning("App is shutting down; rejecting upload attempt.")
        raise HTTPException(
            status_code=503,
            detail="Server is shutting down. Uploads temporarily unavailable.",
        )

    logger.info("Uploading files...")

    results = await asyncio.gather(
        *(_process_upload(file, uploader_ip) for file in files)
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
async def view_photos(request: Request):
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
async def serve_photo(filename: str, request: Request):
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
async def veggies():
    """Oh, where is my hairbrush?"""
    logger.warning("No hair for my hairbrush!")
    return RedirectResponse(url="https://www.youtube.com/watch?v=i3fL5e4ECYs")
