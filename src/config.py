import os

from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from transformers import AutoImageProcessor, AutoModelForImageClassification

# valid creds
load_dotenv()
NAME = os.getenv("NAME", "My Dog")
POSTGRES_APP_PW = os.getenv("POSTGRES_PW")

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

# image classifier
_wd = os.getcwd()
_model_path = f"{_wd}/models/efficientnet-b0-dog-classifier"
processor = AutoImageProcessor.from_pretrained(_model_path)
model = AutoModelForImageClassification.from_pretrained(_model_path)
