# tests/test_quest_completions.py
from models.enrollment_model import Enrollment, EnrollmentRequest
from models.quest_model import Quest
from models.quest_completion_model import QuestCompletion
from models.user_model import User
from tests.conftest import unique, auth_header


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
