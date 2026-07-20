# tests/test_quests.py
from models.enrollment_model import Enrollment, EnrollmentRequest
from models.quest_completion_model import QuestCompletion
from models.quest_model import Quest
from models.section_model import Section
from tests.conftest import unique, auth_header


def test_create_quest_requires_teacher_owner(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/quests",
        json={
            "title": unique("Quest"),
            "description": "do a thing",
            "category": "academic",
            "point_value": 10,
            "quest_type": "daily",
            "assigned_to": "all",
        },
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 403

    resp = client.post(
        f"/api/sections/{world.section_id}/quests",
        json={
            "title": unique("Quest"),
            "description": "do a thing",
            "category": "academic",
            "point_value": 10,
            "quest_type": "daily",
            "assigned_to": "all",
        },
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["assigned_to"] == "all"
    assert body["point_value"] == 10
    cleanup(Quest, body["quest_id"])


def test_create_social_quest_applies_point_multiplier(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/quests",
        json={
            "title": unique("SocialQuest"),
            "description": "socialize",
            "category": "social",
            "point_value": 10,
            "quest_type": "weekly",
            "assigned_to": "all",
        },
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["point_value"] == 15
    cleanup(Quest, body["quest_id"])


def test_create_quest_assigned_to_specific_student(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/quests",
        json={
            "title": unique("Quest"),
            "description": "just for you",
            "category": "academic",
            "point_value": 20,
            "quest_type": "monthly",
            "assigned_to": world.student_id,
        },
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["assigned_to"] == world.student_id
    cleanup(Quest, body["quest_id"])


def test_list_quests_category_filter(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/quests",
        json={
            "title": unique("Quest"),
            "description": "d",
            "category": "academic",
            "point_value": 10,
            "quest_type": "daily",
            "assigned_to": "all",
        },
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    quest_id = resp.json()["quest_id"]
    cleanup(Quest, quest_id)

    resp = client.get(
        f"/api/sections/{world.section_id}/quests?category=academic",
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 200, resp.text
    assert any(q["quest_id"] == quest_id for q in resp.json())

    resp = client.get(
        f"/api/sections/{world.section_id}/quests?category=bogus",
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 400


def test_delete_quest_requires_owner_teacher(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/quests",
        json={
            "title": unique("Quest"),
            "description": "d",
            "category": "academic",
            "point_value": 10,
            "quest_type": "daily",
            "assigned_to": "all",
        },
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    quest_id = resp.json()["quest_id"]
    cleanup(Quest, quest_id)

    resp = client.delete(f"/api/quests/{quest_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 403

    resp = client.delete(f"/api/quests/{quest_id}", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text


def _create_section_with_student_enrolled(client, world, db, cleanup):
    resp = client.post(
        "/api/sections",
        json={"class_id": world.class_id, "period": unique("Period"), "capacity": 30},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    section_id = resp.json()["section_id"]
    cleanup(Section, section_id)

    resp = client.post(
        f"/api/sections/{section_id}/enrollment-requests",
        headers=auth_header(world.student_token),
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

    enrollment = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.student_id == world.student_id,
    ).first()
    assert enrollment is not None
    cleanup(Enrollment, enrollment.enrollment_id)

    return section_id


def _create_quest(client, section_id, teacher_token, cleanup):
    resp = client.post(
        f"/api/sections/{section_id}/quests",
        json={
            "title": unique("Quest"),
            "description": "d",
            "category": "academic",
            "point_value": 10,
            "quest_type": "daily",
            "assigned_to": "all",
        },
        headers=auth_header(teacher_token),
    )
    assert resp.status_code == 201, resp.text
    quest_id = resp.json()["quest_id"]
    cleanup(Quest, quest_id)
    return quest_id


def test_batch_quests_returns_across_multiple_sections(client, world, db, cleanup):
    quest_id_a = _create_quest(client, world.section_id, world.teacher_token, cleanup)
    other_section_id = _create_section_with_student_enrolled(client, world, db, cleanup)
    quest_id_b = _create_quest(client, other_section_id, world.teacher_token, cleanup)

    resp = client.get(
        f"/api/quests?section_ids={world.section_id}&section_ids={other_section_id}",
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    by_id = {q["quest_id"]: q for q in body}
    assert quest_id_a in by_id
    assert quest_id_b in by_id
    assert by_id[quest_id_a]["section_id"] == world.section_id
    assert by_id[quest_id_b]["section_id"] == other_section_id
    assert by_id[quest_id_a]["completed"] is False


def test_batch_quests_marks_completed_per_student(client, world, cleanup):
    quest_id = _create_quest(client, world.section_id, world.teacher_token, cleanup)

    resp = client.post(f"/api/quests/{quest_id}/complete", headers=auth_header(world.student_token))
    assert resp.status_code == 201, resp.text
    cleanup(QuestCompletion, resp.json()["quest_completion_id"])

    resp = client.get(
        f"/api/quests?section_ids={world.section_id}",
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 200, resp.text
    by_id = {q["quest_id"]: q for q in resp.json()}
    assert by_id[quest_id]["completed"] is True


def test_batch_quests_silently_drops_inaccessible_sections(client, world, cleanup):
    quest_id = _create_quest(client, world.section_id, world.teacher_token, cleanup)

    # A section the student is NOT enrolled in, with its own quest
    resp = client.post(
        "/api/sections",
        json={"class_id": world.class_id, "period": unique("Period"), "capacity": 30},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    other_section_id = resp.json()["section_id"]
    cleanup(Section, other_section_id)
    other_quest_id = _create_quest(client, other_section_id, world.teacher_token, cleanup)

    resp = client.get(
        f"/api/quests?section_ids={world.section_id}&section_ids={other_section_id}",
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 200, resp.text
    quest_ids = {q["quest_id"] for q in resp.json()}
    assert quest_id in quest_ids
    assert other_quest_id not in quest_ids


def test_batch_quests_requires_section_ids_param(client, world):
    resp = client.get("/api/quests", headers=auth_header(world.student_token))
    assert resp.status_code == 422
