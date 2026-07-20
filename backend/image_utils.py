import io
import uuid

from fastapi import HTTPException
from PIL import Image

from supabase_client import supabase

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_DIMENSION = 512
ALLOWED_FORMATS = {"JPEG", "PNG"}

AVATAR_BUCKET = "avatars"
# Path segment supabase-py's get_public_url() embeds in every public bucket URL.
AVATAR_URL_MARKER = f"/storage/v1/object/public/{AVATAR_BUCKET}/"


def save_avatar_image(raw_bytes: bytes) -> str:
    """Validate that raw_bytes is a genuine JPEG or PNG, then re-encode it as a
    normalized JPEG and upload it to Supabase Storage. Re-encoding (rather than
    trusting the upload as-is) strips any non-image payload smuggled past the
    file extension/content-type and guarantees the stored file is exactly what
    it claims to be.

    Returns the public URL of the uploaded file.
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

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)

    filename = f"{uuid.uuid4().hex}.jpg"
    supabase.storage.from_(AVATAR_BUCKET).upload(
        filename, buffer.getvalue(), {"content-type": "image/jpeg"}
    )

    return supabase.storage.from_(AVATAR_BUCKET).get_public_url(filename)


def delete_avatar_image(url: str) -> None:
    if not url or AVATAR_URL_MARKER not in url:
        return
    filename = url.split(AVATAR_URL_MARKER, 1)[1]
    if "/" in filename or ".." in filename:
        return
    supabase.storage.from_(AVATAR_BUCKET).remove([filename])
