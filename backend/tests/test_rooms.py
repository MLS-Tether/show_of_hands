# tests/test_rooms.py
from models.help_request_model import HelpRequest, HelpRequestAcceptance
from models.study_room_model import StudyRoom, RoomMember
from tests.conftest import auth_header
from tests.test_help_requests import _enroll_new_student


def _new_room(client, world, cleanup, group_size=3):
    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Need help", "group_size": group_size, "duration_minutes": 30},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    hr_id = resp.json()["help_request_id"]
    cleanup(HelpRequest, hr_id)

    classmate_id, classmate_token = _enroll_new_student(client, world, cleanup)

    resp = client.post(f"/api/help-requests/{hr_id}/accept", headers=auth_header(classmate_token))
    assert resp.status_code == 200, resp.text
    room_id = resp.json()["room_id"]
    cleanup(StudyRoom, room_id)
    cleanup(RoomMember, room_id=room_id, user_id=world.student_id)
    cleanup(RoomMember, room_id=room_id, user_id=classmate_id)
    cleanup(HelpRequestAcceptance, help_request_id=hr_id, user_id=classmate_id)

    return hr_id, room_id, classmate_id, classmate_token


def test_get_room_membership_rules(client, world, cleanup):
    hr_id, room_id, classmate_id, classmate_token = _new_room(client, world, cleanup)

    resp = client.get(f"/api/rooms/{room_id}", headers=auth_header(classmate_token))
    assert resp.status_code == 200, resp.text

    other_id, other_token = _enroll_new_student(client, world, cleanup)
    resp = client.get(f"/api/rooms/{room_id}", headers=auth_header(other_token))
    assert resp.status_code == 403

    resp = client.get(f"/api/rooms/{room_id}", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text


def test_kick_requires_requester_and_not_self(client, world, cleanup):
    hr_id, room_id, classmate_id, classmate_token = _new_room(client, world, cleanup)

    resp = client.post(
        f"/api/rooms/{room_id}/kick",
        json={"user_id": classmate_id},
        headers=auth_header(classmate_token),
    )
    assert resp.status_code == 403

    resp = client.post(
        f"/api/rooms/{room_id}/kick",
        json={"user_id": world.student_id},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 400


def test_kick_member_auto_closes_room_at_last_member(client, world, cleanup):
    hr_id, room_id, classmate_id, classmate_token = _new_room(client, world, cleanup)

    resp = client.post(
        f"/api/rooms/{room_id}/kick",
        json={"user_id": classmate_id},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/rooms/{room_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "closed"


def test_extend_room_requires_active(client, world, cleanup):
    hr_id, room_id, classmate_id, classmate_token = _new_room(client, world, cleanup)

    resp = client.post(f"/api/rooms/{room_id}/extend", headers=auth_header(classmate_token))
    assert resp.status_code == 403

    resp = client.get(f"/api/rooms/{room_id}", headers=auth_header(world.student_token))
    before = resp.json()["timer_ends_at"]

    resp = client.post(f"/api/rooms/{room_id}/extend", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["timer_ends_at"] > before

    resp = client.post(f"/api/rooms/{room_id}/close", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text

    resp = client.post(f"/api/rooms/{room_id}/extend", headers=auth_header(world.student_token))
    assert resp.status_code == 409


def test_close_room(client, world, cleanup):
    hr_id, room_id, classmate_id, classmate_token = _new_room(client, world, cleanup)

    resp = client.post(f"/api/rooms/{room_id}/close", headers=auth_header(classmate_token))
    assert resp.status_code == 403

    resp = client.post(f"/api/rooms/{room_id}/close", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text

    resp = client.post(f"/api/rooms/{room_id}/close", headers=auth_header(world.student_token))
    assert resp.status_code == 409


def test_delete_room_requester_only(client, world, cleanup):
    hr_id, room_id, classmate_id, classmate_token = _new_room(client, world, cleanup)

    resp = client.delete(f"/api/rooms/{room_id}", headers=auth_header(classmate_token))
    assert resp.status_code == 403

    resp = client.delete(f"/api/rooms/{room_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text

    # Room is gone entirely, not just closed.
    resp = client.get(f"/api/rooms/{room_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 404

    resp = client.get(
        f"/api/sections/{world.section_id}/help-requests",
        headers=auth_header(world.teacher_token),
    )
    hr = [r for r in resp.json() if r["help_request_id"] == hr_id][0]
    assert hr["status"] == "closed"


def test_delete_room_allowed_while_active(client, world, cleanup):
    hr_id, room_id, classmate_id, classmate_token = _new_room(client, world, cleanup)

    resp = client.get(f"/api/rooms/{room_id}", headers=auth_header(world.student_token))
    assert resp.json()["status"] == "active"

    resp = client.delete(f"/api/rooms/{room_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
