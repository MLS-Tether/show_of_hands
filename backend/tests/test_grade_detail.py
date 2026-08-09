# tests/test_grade_detail.py
from db.pool import SessionLocal
from models.assignment_model import Assignment
from models.enrollment_model import Enrollment, EnrollmentRequest
from models.help_request_model import HelpRequest, HelpRequestAcceptance
from models.study_room_model import StudyRoom, RoomMember
from models.submission_model import Submission
from models.user_model import User
from tests.conftest import unique, auth_header


def _enroll_new_student(client, world, cleanup):
    username = unique("classmate")
    resp = client.post("/api/auth/register", json={
        "username": username,
        "full_name": "Class Mate",
        "password": "password123",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["user_id"]
    cleanup(User, user_id)

    resp = client.post("/api/auth/login", json={"username": username, "password": "password123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]

    resp = client.post(f"/api/sections/{world.section_id}/enrollment-requests", headers=auth_header(token))
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["enrollment_request_id"]
    cleanup(EnrollmentRequest, request_id)

    resp = client.patch(
        f"/api/enrollment-requests/{request_id}",
        json={"status": "accepted"},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text

    db = SessionLocal()
    enrollment = db.query(Enrollment).filter(
        Enrollment.section_id == world.section_id,
        Enrollment.student_id == user_id,
    ).first()
    enrollment_id = enrollment.enrollment_id
    db.close()
    cleanup(Enrollment, enrollment_id)

    return user_id, username, token


def _new_assignment(client, world, cleanup, point_value=100, due_date="2027-01-01T00:00:00Z"):
    resp = client.post(
        f"/api/sections/{world.section_id}/assignments",
        json={"title": unique("HW"), "due_date": due_date, "point_value": point_value},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    assignment_id = resp.json()["assignment_id"]
    cleanup(Assignment, assignment_id)
    return assignment_id


def _submit(client, world, cleanup, assignment_id, student_token=None):
    resp = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        json={},
        headers=auth_header(student_token or world.student_token),
    )
    assert resp.status_code == 201, resp.text
    submission_id = resp.json()["submission_id"]
    cleanup(Submission, submission_id)
    return submission_id


def _grade_and_finalize(client, world, submission_id, grade):
    resp = client.patch(
        f"/api/submissions/{submission_id}/grade",
        json={"grade": grade},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/api/submissions/{submission_id}/finalize", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text


def test_detail_matches_grades_endpoint_and_lists_assignments(client, world, cleanup):
    graded_id = _new_assignment(client, world, cleanup)
    submission_id = _submit(client, world, cleanup, graded_id)
    _grade_and_finalize(client, world, submission_id, 85)

    ungraded_id = _new_assignment(client, world, cleanup, due_date="2027-06-01T00:00:00Z")

    resp = client.get(
        f"/api/sections/{world.section_id}/grades/{world.student_id}",
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    grade = resp.json()

    resp = client.get(
        f"/api/sections/{world.section_id}/grades/{world.student_id}/detail",
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    detail = resp.json()

    assert detail["percentage"] == grade["percentage"]
    assert detail["letter_grade"] == grade["letter_grade"]

    items_by_id = {a["assignment_id"]: a for a in detail["assignments"]}
    assert items_by_id[graded_id]["status"] == "graded"
    assert items_by_id[graded_id]["grade"] == 85
    assert items_by_id[graded_id]["submitted_at"] is not None
    assert items_by_id[ungraded_id]["status"] == "not_submitted"
    assert items_by_id[ungraded_id]["grade"] is None
    assert items_by_id[ungraded_id]["submitted_at"] is None
    assert detail["study_rooms"] == []


def test_detail_marks_submission_as_late_when_submitted_after_due_date(client, world, cleanup):
    # Due date in the past -- any submission created now is necessarily late.
    assignment_id = _new_assignment(client, world, cleanup, due_date="2020-01-01T00:00:00Z")
    submission_id = _submit(client, world, cleanup, assignment_id)

    resp = client.get(
        f"/api/sections/{world.section_id}/grades/{world.student_id}/detail",
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    item = next(a for a in resp.json()["assignments"] if a["assignment_id"] == assignment_id)
    assert item["submitted_at"] is not None
    assert item["submitted_at"] > item["due_date"]


def test_detail_only_lists_rooms_requested_by_this_student(client, world, cleanup):
    classmate_id, classmate_username, classmate_token = _enroll_new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Detail room test", "group_size": 2, "duration_minutes": 30},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    hr_id = resp.json()["help_request_id"]
    cleanup(HelpRequest, hr_id)

    resp = client.post(f"/api/help-requests/{hr_id}/accept", headers=auth_header(classmate_token))
    assert resp.status_code == 200, resp.text
    room_id = resp.json()["room_id"]
    cleanup(StudyRoom, room_id)
    cleanup(RoomMember, room_id=room_id, user_id=world.student_id)
    cleanup(RoomMember, room_id=room_id, user_id=classmate_id)
    cleanup(HelpRequestAcceptance, help_request_id=hr_id, user_id=classmate_id)

    resp = client.get(
        f"/api/sections/{world.section_id}/grades/{world.student_id}/detail",
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    rooms_by_id = {r["room_id"]: r for r in body["study_rooms"]}
    assert room_id in rooms_by_id
    room = rooms_by_id[room_id]
    assert room["topic"] == "Detail room test"
    member_usernames = {m["username"] for m in room["members"]}
    assert member_usernames == {world.student_username, classmate_username}

    # The classmate (the room's acceptor, not its requester) should see no
    # rooms in their own detail view for this section.
    resp = client.get(
        f"/api/sections/{world.section_id}/grades/{classmate_id}/detail",
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["study_rooms"] == []


def test_detail_forbidden_for_student(client, world):
    resp = client.get(
        f"/api/sections/{world.section_id}/grades/{world.student_id}/detail",
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 403


def test_detail_forbidden_for_non_owning_teacher(client, world, cleanup):
    other_teacher_username = unique("teacher2")
    resp = client.post("/api/auth/register", json={
        "username": other_teacher_username,
        "password": "password123",
        "full_name": "Test Teacher",
        "school_code": world.school_code,
        "role": "teacher",
    })
    assert resp.status_code == 201, resp.text
    other_teacher_id = resp.json()["user_id"]
    cleanup(User, other_teacher_id)

    resp = client.patch(f"/api/users/{other_teacher_id}/verify", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text

    resp = client.post("/api/auth/login", json={
        "username": other_teacher_username,
        "password": "password123",
    })
    assert resp.status_code == 200, resp.text
    other_teacher_token = resp.json()["access_token"]

    resp = client.get(
        f"/api/sections/{world.section_id}/grades/{world.student_id}/detail",
        headers=auth_header(other_teacher_token),
    )
    assert resp.status_code == 403


def test_detail_not_found_for_unenrolled_student(client, world, cleanup):
    username = unique("outsider")
    resp = client.post("/api/auth/register", json={
        "username": username,
        "full_name": "Test Outsider",
        "password": "password123",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    outsider_id = resp.json()["user_id"]
    cleanup(User, outsider_id)

    resp = client.get(
        f"/api/sections/{world.section_id}/grades/{outsider_id}/detail",
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 404


def test_detail_unauthenticated(client, world):
    resp = client.get(f"/api/sections/{world.section_id}/grades/{world.student_id}/detail")
    assert resp.status_code == 401
