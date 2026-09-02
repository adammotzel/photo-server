from fastapi.templating import Jinja2Templates

from src.config import Config

config = Config()  # ty: ignore[missing-argument]

UPLOAD_FOLDER = "photos"
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
ALLOWED_MIME_TYPES = ("image/jpeg", "image/png", "image/gif", "image/webp")

PHOTOS_PAGE_SIZE = 24
THUMBNAIL_SUBDIR = "thumbnails"
THUMBNAIL_MAX_PX = 480
THUMBNAIL_QUALITY = 75
PHOTO_CACHE_HEADERS = {"Cache-Control": "public, max-age=31536000, immutable"}

MODEL_PATH = "models/efficientnet-b0-dog-classifier"

templates = Jinja2Templates(directory="src/templates")
