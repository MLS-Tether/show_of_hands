# tests/test_quest_completions.py
import io

import pytest
from PIL import Image

import quest_submission_utils as qsu
from models.enrollment_model import Enrollment, EnrollmentRequest
from models.quest_model import Quest
from models.quest_completion_model import QuestCompletion
from models.user_model import User
from tests.conftest import unique, auth_header


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
    image = Image.new("RGB", (10, 10), color="blue")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def _new_quest(client, world, cleanup, assigned_to="all", point_value=20):
    resp = client.post(
        f"/api/sections/{world.section_id}/quests",
        json={
            "title": unique("Quest"),
            "description": "d",
            "category": "academic",
            "point_value": point_value,
            "quest_type": "daily",
            "assigned_to": assigned_to,
        },
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    quest_id = resp.json()["quest_id"]
    cleanup(Quest, quest_id)
    return quest_id


def test_complete_quest_awards_points(client, world, cleanup):
    quest_id = _new_quest(client, world, cleanup, point_value=20)

    resp = client.post(f"/api/quests/{quest_id}/complete", headers=auth_header(world.student_token))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["points_awarded"] == 20
    cleanup(QuestCompletion, body["quest_completion_id"])


def test_complete_quest_already_completed(client, world, cleanup):
    quest_id = _new_quest(client, world, cleanup)

    resp = client.post(f"/api/quests/{quest_id}/complete", headers=auth_header(world.student_token))
    assert resp.status_code == 201, resp.text
    cleanup(QuestCompletion, resp.json()["quest_completion_id"])

    resp = client.post(f"/api/quests/{quest_id}/complete", headers=auth_header(world.student_token))
    assert resp.status_code == 409


def test_complete_quest_not_assigned_to_you(client, world, db, cleanup):
    # A quest assigned to a *different* enrolled student — not world.teacher_id,
    # since create_quest requires assigned_to to be a student actually
    # enrolled in the section, which a teacher never is.
    other_username = unique("other_student")
    resp = client.post("/api/auth/register", json={
        "username": other_username,
        "full_name": "Other Student",
        "password": "password123",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    other_student_id = resp.json()["user_id"]
    cleanup(User, other_student_id)

    resp = client.post("/api/auth/login", json={"username": other_username, "password": "password123"})
    assert resp.status_code == 200, resp.text
    other_student_token = resp.json()["access_token"]

    resp = client.post(
        f"/api/sections/{world.section_id}/enrollment-requests",
        headers=auth_header(other_student_token),
    )
    assert resp.status_code == 201, resp.text
    enrollment_request_id = resp.json()["enrollment_request_id"]
    cleanup(EnrollmentRequest, enrollment_request_id)

    resp = client.patch(
        f"/api/enrollment-requests/{enrollment_request_id}",
        json={"status": "accepted"},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text

    enrollment = db.query(Enrollment).filter(
        Enrollment.section_id == world.section_id,
        Enrollment.student_id == other_student_id,
    ).first()
    assert enrollment is not None
    cleanup(Enrollment, enrollment.enrollment_id)

    quest_id = _new_quest(client, world, cleanup, assigned_to=other_student_id)

    resp = client.post(f"/api/quests/{quest_id}/complete", headers=auth_header(world.student_token))
    assert resp.status_code == 403


def test_complete_quest_with_description_only(client, world, cleanup):
    quest_id = _new_quest(client, world, cleanup)

    resp = client.post(
        f"/api/quests/{quest_id}/complete",
        data={"description": "Read two chapters and wrote a summary."},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["description"] == "Read two chapters and wrote a summary."
    assert body["file_url"] is None
    cleanup(QuestCompletion, body["quest_completion_id"])


def test_complete_quest_with_no_submission_still_works(client, world, cleanup):
    quest_id = _new_quest(client, world, cleanup)

    resp = client.post(f"/api/quests/{quest_id}/complete", headers=auth_header(world.student_token))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["description"] is None
    assert body["file_url"] is None
    cleanup(QuestCompletion, body["quest_completion_id"])


def test_complete_quest_with_jpeg_upload(client, world, cleanup, fake_supabase):
    quest_id = _new_quest(client, world, cleanup)

    resp = client.post(
        f"/api/quests/{quest_id}/complete",
        data={"description": "Here's proof."},
        files={"file": ("proof.jpg", _make_jpeg_bytes(), "image/jpeg")},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["file_url"].startswith("https://fake.supabase.co")
    assert fake_supabase.storage.bucket.uploaded[0][2]["content-type"] == "image/jpeg"
    cleanup(QuestCompletion, body["quest_completion_id"])


def test_complete_quest_with_pdf_upload(client, world, cleanup, fake_supabase):
    quest_id = _new_quest(client, world, cleanup)

    resp = client.post(
        f"/api/quests/{quest_id}/complete",
        files={"file": ("proof.pdf", qsu.PDF_MAGIC_BYTES + b"1.4\nfake body", "application/pdf")},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["file_url"].startswith("https://fake.supabase.co")
    assert fake_supabase.storage.bucket.uploaded[0][2]["content-type"] == "application/pdf"
    cleanup(QuestCompletion, body["quest_completion_id"])


def test_complete_quest_rejects_disallowed_file_type(client, world, cleanup, fake_supabase):
    quest_id = _new_quest(client, world, cleanup)

    resp = client.post(
        f"/api/quests/{quest_id}/complete",
        files={"file": ("proof.txt", b"not allowed", "text/plain")},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 400
    assert not fake_supabase.storage.bucket.uploaded


def test_complete_quest_rejects_description_too_long(client, world, cleanup):
    quest_id = _new_quest(client, world, cleanup)

    resp = client.post(
        f"/api/quests/{quest_id}/complete",
        data={"description": "x" * 501},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 400


def test_list_quest_completions_returns_submission_details(client, world, cleanup, fake_supabase):
    quest_id = _new_quest(client, world, cleanup)

    resp = client.post(
        f"/api/quests/{quest_id}/complete",
        data={"description": "Finished the reading."},
        files={"file": ("proof.jpg", _make_jpeg_bytes(), "image/jpeg")},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    completion_id = resp.json()["quest_completion_id"]
    cleanup(QuestCompletion, completion_id)

    resp = client.get(f"/api/quests/{quest_id}/completions", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["quest_completion_id"] == completion_id
    assert body[0]["username"] == world.student_username
    assert body[0]["description"] == "Finished the reading."
    assert body[0]["file_url"].startswith("https://fake.supabase.co")


def test_list_quest_completions_requires_teacher_role(client, world, cleanup):
    quest_id = _new_quest(client, world, cleanup)

    resp = client.get(f"/api/quests/{quest_id}/completions", headers=auth_header(world.student_token))
    assert resp.status_code == 403
