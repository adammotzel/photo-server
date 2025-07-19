import os
import re
import shutil
import json
from typing import Set
from datetime import datetime

from fastapi import UploadFile


def save_photo(file_location: str, file: UploadFile, user: str):
    """
    Write photo to disk along with photo metadata.
    
    Parameters
    --------
    file_location : str
        Path used to save the photo.
    file : UploadFile
        FastAPI UploadFile object.
    user : str
        Name of the user that uploaded the photo.
    """
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # photo metadata
    metadata = {
        "uploaded_by": user,
        "uploaded_time": datetime.utcnow().isoformat() + "Z",
        "original_filename": file.filename,
        "content_type": file.content_type
    }

    json_path = os.path.splitext(file_location)[0] + ".json"
    with open(json_path, "w", encoding="utf-8") as meta_file:
        json.dump(metadata, meta_file, indent=2)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and remove unsafe characters.

        1. Remove path info from filename
        2. Remove unwanted characters

    Parameters
    ----------
    filename : str
        Name of the file, including the file extention.

    Returns
    -------
    str
        Sanitized filename.
    """

    filename = os.path.basename(filename)
    name, ext = os.path.splitext(filename)
    ext = ext.lower()

    name = re.sub(r'[^A-Za-z0-9_.-]', "_", name)

    return f"{name}{ext}"


def get_unique_filename(existing_filenames: Set[str], filename: str) -> str:
    """
    Get a unique filename, if the filename already exists. Sanitze filename 
    before returning the unique name.

    Parameters
    ----------
    existing_filenames : Set[str]
        Existing file names.
    filename : str
        Name of the new file.

    Returns
    -------
    str
        Unique filename.
    """
    
    filename = sanitize_filename(filename)

    base, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename

    while new_filename in existing_filenames:
        new_filename = f"{base}_{counter}{ext}"
        counter += 1

    return new_filename
