import io
import os
import uuid

from fastapi import HTTPException
from PIL import Image

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_DIMENSION = 512
ALLOWED_FORMATS = {"JPEG", "PNG"}

UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), "uploads")
AVATAR_DIR = os.path.join(UPLOAD_ROOT, "avatars")
AVATAR_URL_PREFIX = "/uploads/avatars"

os.makedirs(AVATAR_DIR, exist_ok=True)


def save_avatar_image(raw_bytes: bytes) -> str:
    """Validate that raw_bytes is a genuine JPEG or PNG, then re-encode it as a
    normalized JPEG on disk. Re-encoding (rather than trusting the upload as-is)
    strips any non-image payload smuggled past the file extension/content-type
    and guarantees the stored file is exactly what it claims to be.

    Returns the public URL path to the saved file.
    """
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Image must be 5MB or smaller.")

    try:
        image = Image.open(io.BytesIO(raw_bytes))
        image.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="File is not a valid image.")

    # verify() leaves the image unusable for further ops, so reopen it.
    image = Image.open(io.BytesIO(raw_bytes))
    if image.format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are allowed.")

    image = image.convert("RGB")
    image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

    filename = f"{uuid.uuid4().hex}.jpg"
    path = os.path.join(AVATAR_DIR, filename)
    image.save(path, format="JPEG", quality=85)

    return f"{AVATAR_URL_PREFIX}/{filename}"


def delete_avatar_image(url: str) -> None:
    if not url or not url.startswith(AVATAR_URL_PREFIX + "/"):
        return
    filename = url[len(AVATAR_URL_PREFIX) + 1:]
    if "/" in filename or ".." in filename:
        return
    path = os.path.join(AVATAR_DIR, filename)
    if os.path.isfile(path):
        os.remove(path)
