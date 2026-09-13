import asyncio
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from src.config import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    MODEL_PATH,
    PHOTO_CACHE_HEADERS,
    PHOTOS_PAGE_SIZE,
    UPLOAD_FOLDER,
    config,
    templates,
)
from src.db import (
    get_photo_count,
    get_photos,
    pool,
    upsert_network,
    write_description,
    write_prediction,
)
from src.logger import listener, logger
from src.model import describe_image, inference, load_model
from src.types import PendingDescription, UploadResult
from src.utils import save_photo, thumbnail_path


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown control."""

    app.state.shutting_down = False
    listener.start()
    logger.info("Loading classifier...")
    app.state.processor, app.state.model = load_model(MODEL_PATH)
    logger.info("Setting up database connection pool...")
    pool.open()
    app.state.network_id = upsert_network(config.network_name)
    logger.info(f"App launched on Wi-Fi network '{config.network_name}'")

    yield

    app.state.shutting_down = True
    pool.close()
    logger.info("Shutdown complete.")
    listener.stop()


app = FastAPI(lifespan=lifespan)


# ----- Async utilities -----


async def _process_upload(
    request: Request,
    file: UploadFile,
    uploader_ip: str,
    network_id: int | None,
    pending: list[PendingDescription],
) -> UploadResult:
    """
    Validate, classify, and save a single uploaded photo. Accepted photos are
    appended to `pending` to be described after the response is sent.

    Parameters
    ----------
    request : Request
        API request containing the app state.
    file : UploadFile
        File to upload.
    uploader_ip : str
        LAN IP address of the uploading device.
    network_id : int | None
        'id' of the network the upload was received on.
    pending : list[PendingDescription]
        Collects accepted photos still waiting on a description.

    Returns
    -------
    UploadResult
        Whether the upload was accepted, the client's original filename, the
        name it was stored under (accepted uploads only), and why it was
        rejected (rejected uploads only).
    """

    filename = file.filename or ""

    try:
        ext = os.path.splitext(filename)[-1].lower()

        if ext not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_MIME_TYPES:
            logger.warning(
                f"Rejected file '{filename}': unsupported file type ({file.content_type})."
            )
            return UploadResult(False, filename, reason="unsupported file type")

        # get unique + safe filename
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_location = os.path.join(UPLOAD_FOLDER, unique_filename)

        contents = await file.read()

        # check for dawgs
        predicted_label, confidence = await run_in_threadpool(
            inference,
            request.app.state.processor,
            request.app.state.model,
            contents,
        )

        if predicted_label != "dog":
            logger.warning(
                f"Image '{filename}' rejected. Expected a dog, received '{predicted_label}'"
            )
            await run_in_threadpool(
                write_prediction,
                None,
                network_id,
                filename,
                predicted_label,
                confidence,
                uploader_ip,
            )
            return UploadResult(
                False,
                filename,
                reason=f"not a dog ({predicted_label}, {confidence:.0%})",
            )

        photo_id = await run_in_threadpool(
            save_photo,
            file_location,
            thumbnail_path(UPLOAD_FOLDER, unique_filename),
            contents,
            unique_filename,
            file.content_type,
        )
        await run_in_threadpool(
            write_prediction,
            photo_id,
            network_id,
            filename,
            predicted_label,
            confidence,
            uploader_ip,
        )
        pending.append(PendingDescription(photo_id, filename, contents))
        return UploadResult(True, filename, unique_filename)
    except Exception:
        logger.error("A file uploaded failed.", exc_info=True)
        return UploadResult(False, filename, reason="upload failed")


async def _describe_photo(pending: PendingDescription) -> None:
    """
    Write an LLM description for a saved photo and link it to the photo.

    Best-effort: a photo without a description is still worth keeping, so a
    failed (or unconfigured) LLM call is logged and otherwise ignored.

    Parameters
    ----------
    pending : PendingDescription
        The saved photo to describe.

    Returns
    -------
    None
    """

    try:
        description = await run_in_threadpool(describe_image, pending.contents)
        await run_in_threadpool(
            write_description,
            pending.photo_id,
            description.description,
            description.input_tokens,
            description.output_tokens,
            description.model,
        )
    except Exception:
        logger.warning(
            f"Failed to describe '{pending.original_filename}'; "
            "it will stay without a description.",
            exc_info=True,
        )


async def _describe_photos(pending: list[PendingDescription]) -> None:
    """
    Describe a batch of saved photos concurrently. Runs as a background task,
    after the upload response has been sent.

    Parameters
    ----------
    pending : list[PendingDescription]
        The saved photos to describe.

    Returns
    -------
    None
    """

    logger.info(f"Describing {len(pending)} photo(s) in the background...")
    await asyncio.gather(*(_describe_photo(photo) for photo in pending))


# ---------- ENDPOINTS ----------


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the Home page."""
    return templates.TemplateResponse(request, "index.html", {"name": config.name})


@app.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request):
    """Serve the Upload page."""
    return templates.TemplateResponse(request, "upload.html")


@app.post("/upload")
async def upload_photos(
    request: Request,
    background_tasks: BackgroundTasks,
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

    pending: list[PendingDescription] = []

    results = await asyncio.gather(
        *(
            _process_upload(
                request, file, uploader_ip, request.app.state.network_id, pending
            )
            for file in files
        )
    )

    # fire and forget: LLM descriptions are slow, so the uploader gets their
    # results now and descriptions are written after the response is sent
    if pending:
        background_tasks.add_task(_describe_photos, pending)

    accepted = [result for result in results if result.accepted]
    rejected = [result for result in results if not result.accepted]

    logger.info(
        f"Accepted {len(accepted)} image(s), rejected {len(rejected)} image(s)."
    )

    # the template picks the success / partial / error message from these
    return templates.TemplateResponse(
        request,
        "upload.html",
        {"accepted": accepted, "rejected": rejected},
    )


@app.get("/photos", response_class=HTMLResponse)
async def view_photos(request: Request, page: int = 1):
    """Photo gallery page, paginated newest-upload-first."""

    logger.info(f"Request received to view photo gallery (page {page}).")

    try:
        total_photos = await run_in_threadpool(get_photo_count)
        total_pages = max(-(-total_photos // PHOTOS_PAGE_SIZE), 1)

        page = min(max(page, 1), total_pages)
        offset = (page - 1) * PHOTOS_PAGE_SIZE

        photos = await run_in_threadpool(get_photos, PHOTOS_PAGE_SIZE, offset)

        logger.info(
            f"Surfacing {len(photos)} photos for the gallery (page {page}/{total_pages})."
        )

        return templates.TemplateResponse(
            request,
            "gallery.html",
            {
                "photos": photos,
                "page": page,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
            },
        )

    except Exception:
        logger.error("Failed to fetch photos.", exc_info=True)

        return templates.TemplateResponse(
            request, "gallery.html", {"success": False, "error": True}
        )


@app.get("/thumbnails/{filename}", response_class=FileResponse)
async def serve_thumbnail(filename: str, request: Request):
    """
    Serve gallery-sized thumbnails, keyed by the photo's stored filename.

    Falls back to the full-size original for photos uploaded before thumbnails
    existed, or whose thumbnail failed to render.
    """

    try:
        safe_name = os.path.basename(filename)
        file_path = thumbnail_path(UPLOAD_FOLDER, safe_name)

        media_type = "image/webp"

        if not os.path.exists(file_path):
            logger.warning(
                f"No thumbnail for '{safe_name}'; serving the full-size original."
            )
            file_path = os.path.join(UPLOAD_FOLDER, safe_name)
            media_type = None

        return FileResponse(
            file_path,
            media_type=media_type,
            headers=PHOTO_CACHE_HEADERS,
        )

    except Exception:
        logger.error(f"Failed to fetch thumbnail '{filename}'.", exc_info=True)

        return templates.TemplateResponse(
            request, "gallery.html", {"success": False, "error": True}
        )


@app.get("/photos/{filename}", response_class=FileResponse)
async def serve_photo(filename: str, request: Request):
    """Serve full-size photos, linked to from the gallery."""

    try:
        file_path = os.path.join(UPLOAD_FOLDER, os.path.basename(filename))

        return FileResponse(file_path, headers=PHOTO_CACHE_HEADERS)

    except Exception:
        logger.error(f"Failed to fetch photo '{filename}'.", exc_info=True)

        return templates.TemplateResponse(
            request, "gallery.html", {"success": False, "error": True}
        )


@app.get("/veggietales")
async def veggies():
    """Oh, where is my hairbrush?"""
    logger.warning("No hair for my hairbrush!")
    return RedirectResponse(url="https://www.youtube.com/watch?v=i3fL5e4ECYs")
