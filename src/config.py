import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates

load_dotenv(Path(__file__).resolve().parent / ".env")

NAME = os.environ["NAME"]
NETWORK_NAME = os.environ["NETWORK_NAME"]
POSTGRES_APP_PW = os.environ["POSTGRES_PW"]
DB_HOST = os.environ["DB_HOST"]
DB_PORT = os.environ["DB_PORT"]
DB_USER = os.environ["DB_USER"]

# check for test environment
if os.getenv("TEST_ENV"):
    DB_NAME = os.environ["TEST_DB_NAME"]
else:
    DB_NAME = os.environ["DB_NAME"]

UPLOAD_FOLDER = "src/photos"
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
ALLOWED_MIME_TYPES = ("image/jpeg", "image/png", "image/gif", "image/webp")

templates = Jinja2Templates(directory="src/templates")
