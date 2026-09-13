from fastapi.templating import Jinja2Templates
from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    name: str
    db_password: SecretStr
    network_name: str
    db_host: str
    db_port: int
    db_user: str
    db_name: str


config = Config()  # ty: ignore[missing-argument]

OPENAI_MODEL = "gpt-4o-mini"

# descriptions are written in the background, and shutdown waits for them (see
# timeout_graceful_shutdown in scripts/run.py): bound each call so a hung
# request can't hold shutdown hostage. SDK defaults are 600s and 2 retries
OPENAI_TIMEOUT_S = 30
OPENAI_MAX_RETRIES = 1

# descriptions are generated from a downscaled copy: the vision model tiles
# the image anyway, and base64-ing an 11 MB original is slow and expensive
DESCRIPTION_MAX_PX = 512
DESCRIPTION_QUALITY = 80

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
