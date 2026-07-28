import io
import uuid

from fastapi import HTTPException
from PIL import Image

from supabase_client import supabase

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_DIMENSION = 2000
PDF_MAGIC_BYTES = b"%PDF-"

QUEST_SUBMISSIONS_BUCKET = "quest-submissions"
# Path segment supabase-py's get_public_url() embeds in every public bucket URL.
QUEST_SUBMISSION_URL_MARKER = f"/storage/v1/object/public/{QUEST_SUBMISSIONS_BUCKET}/"


def save_quest_submission_file(raw_bytes: bytes, content_type: str) -> str:
    """Validate that raw_bytes is a genuine JPEG or PDF, then upload it to
    Supabase Storage. JPEGs are re-encoded (rather than trusted as-is) to
    strip any non-image payload smuggled past the content-type; PDFs are
    checked for their magic bytes and stored unmodified since there's no
    lightweight re-encoding step available for them.

    Returns the public URL of the uploaded file.
    """
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File must be 10MB or smaller.")

    if content_type == "image/jpeg":
        try:
            image = Image.open(io.BytesIO(raw_bytes))
            image.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="File is not a valid JPEG image.")

        # verify() leaves the image unusable for further ops, so reopen it.
        image = Image.open(io.BytesIO(raw_bytes))
        if image.format != "JPEG":
            raise HTTPException(status_code=400, detail="File is not a valid JPEG image.")

        image = image.convert("RGB")
        image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        upload_bytes = buffer.getvalue()
        ext = "jpg"
        upload_content_type = "image/jpeg"
    elif content_type == "application/pdf":
        if not raw_bytes.startswith(PDF_MAGIC_BYTES):
            raise HTTPException(status_code=400, detail="File is not a valid PDF.")
        upload_bytes = raw_bytes
        ext = "pdf"
        upload_content_type = "application/pdf"
    else:
        raise HTTPException(status_code=400, detail="Only JPEG images and PDFs are allowed.")

    filename = f"{uuid.uuid4().hex}.{ext}"
    supabase.storage.from_(QUEST_SUBMISSIONS_BUCKET).upload(
        filename, upload_bytes, {"content-type": upload_content_type}
    )

    return supabase.storage.from_(QUEST_SUBMISSIONS_BUCKET).get_public_url(filename)
