# tests/test_quest_completions.py
from models.quest_model import Quest
from models.quest_completion_model import QuestCompletion
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


def test_complete_quest_not_assigned_to_you(client, world, cleanup):
    quest_id = _new_quest(client, world, cleanup, assigned_to=world.teacher_id)

    resp = client.post(f"/api/quests/{quest_id}/complete", headers=auth_header(world.student_token))
    assert resp.status_code == 403
