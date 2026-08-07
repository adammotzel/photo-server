from fastapi.templating import Jinja2Templates

from src.config import Config

_config = Config()  # ty: ignore[missing-argument]

NAME = _config.name
NETWORK_NAME = _config.network_name
DB_HOST = _config.db_host
DB_PORT = _config.db_port
DB_NAME = _config.db_name
DB_PASSWORD = _config.db_password
DB_USER = _config.db_user

UPLOAD_FOLDER = "src/photos"
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
ALLOWED_MIME_TYPES = ("image/jpeg", "image/png", "image/gif", "image/webp")

PHOTOS_PAGE_SIZE = 24

MODEL_PATH = "models/efficientnet-b0-dog-classifier"

templates = Jinja2Templates(directory="src/templates")
