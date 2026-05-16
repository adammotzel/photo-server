import logging
import os

from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates

# custom logger
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H-%M-%S"
)
sh = logging.StreamHandler()
sh.setFormatter(formatter)
logger.addHandler(sh)

# valid creds
load_dotenv()
NAME = os.getenv("NAME", "My Dog")
SECRET = os.getenv("SECRET")
POSTGRES_APP_PW = os.getenv("POSTGRES_PW")

# DB config
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "photoapp"
DB_USER = "photoapp_user"

# file serving
templates = Jinja2Templates(directory="src/templates")

UPLOAD_FOLDER = "src/photos"
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
ALLOWED_MIME_TYPES = ("image/jpeg", "image/png", "image/gif", "image/webp")
