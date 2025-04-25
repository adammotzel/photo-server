import os
import logging
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates


# custom logger
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s: %(message)s", 
    datefmt="%Y-%m-%d %H-%M-%S"
)
sh = logging.StreamHandler()
sh.setFormatter(formatter)
logger.addHandler(sh)

# valid creds
load_dotenv()
PASSWORD = os.getenv("PW")
USERNAMES = os.getenv("UN").split(",")
NAME = os.getenv("NAME", "My Dog")
SECRET = os.getenv("SECRET")

# file serving
templates = Jinja2Templates(directory="src/templates")

UPLOAD_FOLDER = "src/photos"

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp"
}

# for writing photos to disk
save_photo_executor = ThreadPoolExecutor(max_workers=1)

# existing photos
manifest = {
    file for file in os.listdir("src/photos") if file.lower().endswith(
        ('.png', '.jpg', '.jpeg', '.gif', '.webp')
    )
}
