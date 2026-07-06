# tests/test_quests.py
from models.quest_model import Quest
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
