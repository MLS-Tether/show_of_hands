# tests/test_quest_submission_utils.py
import io

import pytest
from fastapi import HTTPException
from PIL import Image

import quest_submission_utils as qsu


class _FakeBucket:
    def __init__(self):
        self.uploaded = []

    def upload(self, filename, data, options):
        self.uploaded.append((filename, data, options))

    def get_public_url(self, filename):
        return f"https://fake.supabase.co{qsu.QUEST_SUBMISSION_URL_MARKER}{filename}"


class _FakeStorage:
    def __init__(self):
        self.bucket = _FakeBucket()

    def from_(self, bucket_name):
        assert bucket_name == qsu.QUEST_SUBMISSIONS_BUCKET
        return self.bucket


class _FakeSupabaseClient:
    def __init__(self):
        self.storage = _FakeStorage()


@pytest.fixture
def fake_supabase(monkeypatch):
    fake = _FakeSupabaseClient()
    monkeypatch.setattr(qsu, "supabase", fake)
    return fake


def _make_jpeg_bytes():
    image = Image.new("RGB", (10, 10), color="red")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_accepts_valid_jpeg(fake_supabase):
    url = qsu.save_quest_submission_file(_make_jpeg_bytes(), "image/jpeg")
    assert url.startswith("https://fake.supabase.co")
    assert fake_supabase.storage.bucket.uploaded[0][2]["content-type"] == "image/jpeg"


def test_accepts_valid_pdf(fake_supabase):
    raw = qsu.PDF_MAGIC_BYTES + b"1.4\n%fake pdf body"
    url = qsu.save_quest_submission_file(raw, "application/pdf")
    assert url.startswith("https://fake.supabase.co")
    uploaded_name, uploaded_bytes, uploaded_options = fake_supabase.storage.bucket.uploaded[0]
    assert uploaded_name.endswith(".pdf")
    assert uploaded_bytes == raw
    assert uploaded_options["content-type"] == "application/pdf"


def test_rejects_fake_pdf(fake_supabase):
    with pytest.raises(HTTPException) as exc_info:
        qsu.save_quest_submission_file(b"not a real pdf", "application/pdf")
    assert exc_info.value.status_code == 400
    assert not fake_supabase.storage.bucket.uploaded


def test_rejects_corrupt_jpeg(fake_supabase):
    with pytest.raises(HTTPException) as exc_info:
        qsu.save_quest_submission_file(b"not a real jpeg", "image/jpeg")
    assert exc_info.value.status_code == 400
    assert not fake_supabase.storage.bucket.uploaded


def test_rejects_disallowed_content_type(fake_supabase):
    with pytest.raises(HTTPException) as exc_info:
        qsu.save_quest_submission_file(b"whatever", "image/gif")
    assert exc_info.value.status_code == 400
    assert not fake_supabase.storage.bucket.uploaded


def test_rejects_oversized_file(fake_supabase):
    raw = qsu.PDF_MAGIC_BYTES + b"0" * (qsu.MAX_UPLOAD_BYTES + 1)
    with pytest.raises(HTTPException) as exc_info:
        qsu.save_quest_submission_file(raw, "application/pdf")
    assert exc_info.value.status_code == 400
    assert not fake_supabase.storage.bucket.uploaded
