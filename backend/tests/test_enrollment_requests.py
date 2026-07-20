# tests/test_enrollment_requests.py
from models.section_model import Section
from models.user_model import User
from models.enrollment_model import Enrollment, EnrollmentRequest
from tests.conftest import unique, auth_header


def _new_section(client, world, cleanup):
    resp = client.post("/api/sections", json={
        "class_id": world.class_id,
        "period": unique("Period"),
        "capacity": 5,
    }, headers=auth_header(world.teacher_token))
    assert resp.status_code == 201, resp.text
    section_id = resp.json()["section_id"]
    cleanup(Section, section_id)
    return section_id


def _new_student(client, world, cleanup):
    username = unique("enrollee")
    resp = client.post("/api/auth/register", json={
        "username": username,
        "full_name": "New Enrollee",
        "password": "password123",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["user_id"]
    cleanup(User, user_id)

    resp = client.post("/api/auth/login", json={"username": username, "password": "password123"})
    assert resp.status_code == 200, resp.text
    return user_id, resp.json()["access_token"]


def test_create_enrollment_request(client, world, cleanup):
    section_id = _new_section(client, world, cleanup)
    student_id, student_token = _new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{section_id}/enrollment-requests",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["student_id"] == student_id
    cleanup(EnrollmentRequest, body["enrollment_request_id"])


def test_create_enrollment_request_duplicate(client, world, cleanup):
    section_id = _new_section(client, world, cleanup)
    _student_id, student_token = _new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{section_id}/enrollment-requests",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 201, resp.text
    cleanup(EnrollmentRequest, resp.json()["enrollment_request_id"])

    resp = client.post(
        f"/api/sections/{section_id}/enrollment-requests",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 409


def test_create_enrollment_request_already_enrolled(client, world):
    resp = client.post(
        f"/api/sections/{world.section_id}/enrollment-requests",
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 409


def test_list_enrollment_requests_pending_only(client, world, cleanup):
    section_id = _new_section(client, world, cleanup)
    _student_id, student_token = _new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{section_id}/enrollment-requests",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["enrollment_request_id"]
    cleanup(EnrollmentRequest, request_id)

    resp = client.get(
        f"/api/sections/{section_id}/enrollment-requests",
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    assert any(r["enrollment_request_id"] == request_id for r in resp.json())

    resp = client.get(
        f"/api/sections/{section_id}/enrollment-requests",
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 403


def test_approve_enrollment_request(client, world, cleanup):
    section_id = _new_section(client, world, cleanup)
    student_id, student_token = _new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{section_id}/enrollment-requests",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["enrollment_request_id"]
    cleanup(EnrollmentRequest, request_id)

    resp = client.patch(
        f"/api/enrollment-requests/{request_id}",
        json={"status": "accepted"},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "accepted"

    resp = client.get(f"/api/sections/{section_id}", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert any(s["user_id"] == student_id for s in body["students"])
    enrollment = [s for s in body["students"] if s["user_id"] == student_id][0]
    # find the created Enrollment row for cleanup
    from db.pool import SessionLocal
    db = SessionLocal()
    row = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.student_id == student_id,
    ).first()
    db.close()
    cleanup(Enrollment, row.enrollment_id)


def test_reject_enrollment_request(client, world, cleanup):
    section_id = _new_section(client, world, cleanup)
    _student_id, student_token = _new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{section_id}/enrollment-requests",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["enrollment_request_id"]
    cleanup(EnrollmentRequest, request_id)

    resp = client.patch(
        f"/api/enrollment-requests/{request_id}",
        json={"status": "rejected"},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"


def test_patch_enrollment_request_requires_section_owner(client, world, cleanup):
    section_id = _new_section(client, world, cleanup)
    _student_id, student_token = _new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{section_id}/enrollment-requests",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["enrollment_request_id"]
    cleanup(EnrollmentRequest, request_id)

    # a second teacher, not the section owner
    other_username = unique("otherteacher")
    resp = client.post("/api/auth/register", json={
        "username": other_username,
        "full_name": "Other Teacher",
        "password": "password123",
        "school_code": world.school_code,
        "role": "teacher",
    })
    assert resp.status_code == 201, resp.text
    other_teacher_id = resp.json()["user_id"]
    cleanup(User, other_teacher_id)
    resp = client.patch(f"/api/users/{other_teacher_id}/verify", headers=auth_header(world.admin_token))
    assert resp.status_code == 200
    resp = client.post("/api/auth/login", json={"username": other_username, "password": "password123"})
    assert resp.status_code == 200, resp.text
    other_teacher_token = resp.json()["access_token"]

    resp = client.patch(
        f"/api/enrollment-requests/{request_id}",
        json={"status": "accepted"},
        headers=auth_header(other_teacher_token),
    )
    assert resp.status_code == 403


def test_drop_student_from_section(client, world, cleanup):
    section_id = _new_section(client, world, cleanup)
    student_id, student_token = _new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{section_id}/enrollment-requests",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["enrollment_request_id"]
    cleanup(EnrollmentRequest, request_id)

    resp = client.patch(
        f"/api/enrollment-requests/{request_id}",
        json={"status": "accepted"},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text

    from db.pool import SessionLocal
    db = SessionLocal()
    row = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.student_id == student_id,
    ).first()
    db.close()
    cleanup(Enrollment, row.enrollment_id)

    resp = client.delete(
        f"/api/sections/{section_id}/students/{student_id}",
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 403  # only admin allowed

    resp = client.delete(
        f"/api/sections/{section_id}/students/{student_id}",
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text
