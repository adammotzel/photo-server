import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates

# valid creds
load_dotenv(Path(__file__).resolve().parent / ".env")
NAME = os.getenv("NAME", "My Dog")
POSTGRES_APP_PW = os.environ["POSTGRES_PW"]

# DB config
DB_HOST = "localhost"
DB_PORT = "5432"

if os.getenv("ENVIRONMENT") == "test":
    DB_NAME = "photoapp_test"
else:
    DB_NAME = "photoapp"

DB_USER = "photoapp_user"

# file serving
templates = Jinja2Templates(directory="src/templates")

UPLOAD_FOLDER = "src/photos"
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
ALLOWED_MIME_TYPES = ("image/jpeg", "image/png", "image/gif", "image/webp")
