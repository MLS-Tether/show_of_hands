# tests/test_help_requests.py
from db.pool import SessionLocal
from models.user_model import User
from models.enrollment_model import Enrollment, EnrollmentRequest
from models.help_request_model import HelpRequest, HelpRequestAcceptance
from models.notification_model import Notification, NotificationTypeEnum
from models.study_room_model import StudyRoom, RoomMember
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

    resp = client.post(
        f"/api/sections/{world.section_id}/enrollment-requests",
        headers=auth_header(token),
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

    db = SessionLocal()
    enrollment = db.query(Enrollment).filter(
        Enrollment.section_id == world.section_id,
        Enrollment.student_id == user_id,
    ).first()
    db.close()
    cleanup(Enrollment, enrollment.enrollment_id)

    return user_id, token


def test_create_help_request(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Need help", "group_size": 2, "duration_minutes": 30},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "open"
    assert body["current_size"] == 1
    cleanup(HelpRequest, body["help_request_id"])


def test_list_my_help_requests_across_sections(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Aggregate endpoint test", "group_size": 2, "duration_minutes": 30},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    hr_id = resp.json()["help_request_id"]
    cleanup(HelpRequest, hr_id)

    resp = client.get("/api/help-requests", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    mine = [r for r in resp.json() if r["help_request_id"] == hr_id][0]
    assert mine["section_id"] == world.section_id
    assert mine["section_name"]
    assert mine["topic"] == "Aggregate endpoint test"
    assert "requester_id" not in mine

    resp = client.get("/api/help-requests", headers=auth_header(world.teacher_token))
    assert resp.status_code == 403


def test_create_help_request_notifies_classmates_not_requester(client, world, cleanup):
    classmate_id, classmate_token = _enroll_new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Need help with recursion", "group_size": 2, "duration_minutes": 30},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    hr_id = resp.json()["help_request_id"]
    cleanup(HelpRequest, hr_id)

    db = SessionLocal()
    classmate_notifications = db.query(Notification).filter(
        Notification.user_id == classmate_id,
        Notification.type == NotificationTypeEnum.new_help_request,
    ).all()
    assert len(classmate_notifications) == 1
    assert "Need help with recursion" in classmate_notifications[0].message
    cleanup(Notification, classmate_notifications[0].notification_id)

    requester_notifications = db.query(Notification).filter(
        Notification.user_id == world.student_id,
        Notification.type == NotificationTypeEnum.new_help_request,
    ).all()
    assert requester_notifications == []
    db.close()

    resp = client.get("/api/notifications", headers=auth_header(classmate_token))
    assert resp.status_code == 200, resp.text
    assert any(n["message"] == "New help request posted: Need help with recursion" for n in resp.json())


def test_list_help_requests_student_vs_teacher_shape(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Need help", "group_size": 2, "duration_minutes": 30},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    hr_id = resp.json()["help_request_id"]
    cleanup(HelpRequest, hr_id)

    resp = client.get(f"/api/sections/{world.section_id}/help-requests", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    student_view = [r for r in resp.json() if r["help_request_id"] == hr_id][0]
    assert "requester_id" not in student_view

    resp = client.get(f"/api/sections/{world.section_id}/help-requests", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    teacher_view = [r for r in resp.json() if r["help_request_id"] == hr_id][0]
    assert teacher_view["requester_id"] == world.student_id


def test_accept_own_help_request_forbidden(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Need help", "group_size": 2, "duration_minutes": 30},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    hr_id = resp.json()["help_request_id"]
    cleanup(HelpRequest, hr_id)

    resp = client.post(f"/api/help-requests/{hr_id}/accept", headers=auth_header(world.student_token))
    assert resp.status_code == 400


def test_accept_help_request_creates_room_and_fills_up(client, world, cleanup):
    classmate_id, classmate_token = _enroll_new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Need help", "group_size": 2, "duration_minutes": 30},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    hr_id = resp.json()["help_request_id"]
    cleanup(HelpRequest, hr_id)

    resp = client.post(f"/api/help-requests/{hr_id}/accept", headers=auth_header(classmate_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "active"
    room_id = body["room_id"]
    cleanup(StudyRoom, room_id)
    cleanup(RoomMember, room_id=room_id, user_id=world.student_id)
    cleanup(RoomMember, room_id=room_id, user_id=classmate_id)
    cleanup(HelpRequestAcceptance, help_request_id=hr_id, user_id=classmate_id)

    resp = client.get(f"/api/rooms/{room_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    member_ids = {m["user_id"] for m in resp.json()["members"]}
    assert member_ids == {world.student_id, classmate_id}


def test_accept_help_request_already_full(client, world, cleanup):
    classmate_id, classmate_token = _enroll_new_student(client, world, cleanup)
    second_id, second_token = _enroll_new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Need help", "group_size": 2, "duration_minutes": 30},
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

    resp = client.post(f"/api/help-requests/{hr_id}/accept", headers=auth_header(second_token))
    assert resp.status_code == 409


def test_leave_then_rejoin_help_request(client, world, cleanup):
    classmate_id, classmate_token = _enroll_new_student(client, world, cleanup)
    second_id, second_token = _enroll_new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Need help", "group_size": 3, "duration_minutes": 30},
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
    cleanup(RoomMember, room_id=room_id, user_id=second_id)
    cleanup(HelpRequestAcceptance, help_request_id=hr_id, user_id=classmate_id)
    cleanup(HelpRequestAcceptance, help_request_id=hr_id, user_id=second_id)

    resp = client.post(f"/api/help-requests/{hr_id}/accept", headers=auth_header(second_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "active"

    # Classmate leaves — group drops below capacity, request reopens, room stays active.
    resp = client.post(f"/api/rooms/{room_id}/leave", headers=auth_header(classmate_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/rooms/{room_id}", headers=auth_header(second_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "active"
    member_ids = {m["user_id"] for m in resp.json()["members"]}
    assert classmate_id not in member_ids

    # Rejoin: previously-accepted-but-departed member can come back without
    # a duplicate acceptance record or a 409 "already accepted" error.
    resp = client.post(f"/api/help-requests/{hr_id}/accept", headers=auth_header(classmate_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "active"

    resp = client.get(f"/api/rooms/{room_id}", headers=auth_header(second_token))
    assert resp.status_code == 200, resp.text
    member_ids = {m["user_id"] for m in resp.json()["members"]}
    assert member_ids == {world.student_id, classmate_id, second_id}


def test_leave_and_rejoin_two_person_room_stays_active(client, world, cleanup):
    """Regression test: in a 2-person group, one member leaving used to drop
    the room straight to 'closed' (remaining <= 1) in the same instant the
    help request reopened for a rejoin, permanently bricking the room's chat
    even after the departed member rejoined. The room must stay active."""
    classmate_id, classmate_token = _enroll_new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Need help", "group_size": 2, "duration_minutes": 30},
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

    resp = client.post(f"/api/rooms/{room_id}/leave", headers=auth_header(classmate_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/rooms/{room_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "active"

    resp = client.post(f"/api/help-requests/{hr_id}/accept", headers=auth_header(classmate_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/rooms/{room_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "active"
    member_ids = {m["user_id"] for m in resp.json()["members"]}
    assert member_ids == {world.student_id, classmate_id}


def test_drop_help_request_requester_only(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Need help", "group_size": 2, "duration_minutes": 30},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    hr_id = resp.json()["help_request_id"]
    cleanup(HelpRequest, hr_id)

    classmate_id, classmate_token = _enroll_new_student(client, world, cleanup)
    resp = client.post(f"/api/help-requests/{hr_id}/drop", headers=auth_header(classmate_token))
    assert resp.status_code == 403

    resp = client.post(f"/api/help-requests/{hr_id}/drop", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text

    # Dropping archives it too, so it disappears from the bulletin board
    # instead of lingering there forever as "closed".
    resp = client.get(
        f"/api/sections/{world.section_id}/help-requests",
        headers=auth_header(world.teacher_token),
    )
    assert not any(r["help_request_id"] == hr_id for r in resp.json())


def test_update_help_request_before_and_after_join(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Need help", "description": "original", "group_size": 2, "duration_minutes": 30},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    hr_id = resp.json()["help_request_id"]
    cleanup(HelpRequest, hr_id)

    classmate_id, classmate_token = _enroll_new_student(client, world, cleanup)

    # Non-requester can't edit.
    resp = client.patch(
        f"/api/help-requests/{hr_id}",
        json={"topic": "Hijacked"},
        headers=auth_header(classmate_token),
    )
    assert resp.status_code == 403

    # Requester can edit freely before anyone else has joined.
    resp = client.patch(
        f"/api/help-requests/{hr_id}",
        json={"topic": "Updated topic", "group_size": 3, "duration_minutes": 45},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["topic"] == "Updated topic"
    assert body["group_size"] == 3
    assert body["duration_minutes"] == 45
    assert body["description"] == "original"

    resp = client.post(f"/api/help-requests/{hr_id}/accept", headers=auth_header(classmate_token))
    assert resp.status_code == 200, resp.text
    room_id = resp.json()["room_id"]
    cleanup(StudyRoom, room_id)
    cleanup(RoomMember, room_id=room_id, user_id=world.student_id)
    cleanup(RoomMember, room_id=room_id, user_id=classmate_id)
    cleanup(HelpRequestAcceptance, help_request_id=hr_id, user_id=classmate_id)

    # Once someone else has joined, editing is blocked.
    resp = client.patch(
        f"/api/help-requests/{hr_id}",
        json={"topic": "Too late"},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 409


def test_confirm_session_awards_points_and_blocks_double_confirm(client, world, cleanup):
    classmate_id, classmate_token = _enroll_new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Need help", "group_size": 2, "duration_minutes": 30},
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

    resp = client.post(
        f"/api/help-requests/{hr_id}/confirm",
        json={"session_occurred": True},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["points_awarded"] == 25

    resp = client.post(
        f"/api/help-requests/{hr_id}/confirm",
        json={"session_occurred": True},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 409


def test_confirm_session_still_works_after_room_closed(client, world, cleanup):
    """Regression test: closing (or deleting) the room archives the help
    request immediately so it drops off the bulletin board, but the requester
    still needs to answer the "did this happen?" prompt afterward. Archiving
    must not 404 that confirm call, or points never get awarded."""
    classmate_id, classmate_token = _enroll_new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Need help", "group_size": 2, "duration_minutes": 30},
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

    resp = client.post(f"/api/rooms/{room_id}/close", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text

    resp = client.post(
        f"/api/help-requests/{hr_id}/confirm",
        json={"session_occurred": True},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["points_awarded"] == 25
