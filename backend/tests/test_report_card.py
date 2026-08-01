# tests/test_report_card.py
from models.assignment_model import Assignment
from models.quest_model import Quest
from models.submission_model import Submission
from models.user_model import User
from tests.conftest import unique, auth_header
from tests.test_help_requests import _enroll_new_student


def _new_assignment(client, world, cleanup, category="homework", point_value=100, due_date="2027-01-01T00:00:00Z"):
    resp = client.post(
        f"/api/sections/{world.section_id}/assignments",
        json={
            "title": unique("HW"),
            "due_date": due_date,
            "point_value": point_value,
            "category": category,
        },
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    assignment_id = resp.json()["assignment_id"]
    cleanup(Assignment, assignment_id)
    return assignment_id


def _new_quest(client, world, cleanup, category="academic", assigned_to="all"):
    resp = client.post(
        f"/api/sections/{world.section_id}/quests",
        json={
            "title": unique("Quest"),
            "description": "do a thing",
            "category": category,
            "point_value": 10,
            "quest_type": "daily",
            "assigned_to": assigned_to,
        },
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    quest_id = resp.json()["quest_id"]
    cleanup(Quest, quest_id)
    return quest_id


def _submit(client, world, cleanup, assignment_id):
    resp = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        json={},
        headers=auth_header(world.student_token),
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


def test_report_card_includes_finalized_and_pending_assignments_and_quests(client, world, cleanup):
    hw = _new_assignment(client, world, cleanup, category="homework")
    quiz = _new_assignment(client, world, cleanup, category="quizzes")
    quest = _new_quest(client, world, cleanup, category="social")

    sub_hw = _submit(client, world, cleanup, hw)
    _grade_and_finalize(client, world, sub_hw, 88)

    # quiz submitted but not graded/finalized -- its grade must not appear.
    _submit(client, world, cleanup, quiz)

    resp = client.get(f"/api/users/{world.student_id}/report_card", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["student_id"] == world.student_id

    section = next(s for s in body["sections"] if s["section_id"] == world.section_id)
    assert section["percentage"] == 88.0
    assert section["letter_grade"] == "B"

    items_by_id = {(i["kind"], i["item_id"]): i for i in section["items"]}

    hw_item = items_by_id[("assignment", hw)]
    assert hw_item["category"] == "homework"
    assert hw_item["grade"] == 88

    quiz_item = items_by_id[("assignment", quiz)]
    assert quiz_item["grade"] is None

    quest_item = items_by_id[("quest", quest)]
    assert quest_item["category"] == "social"
    assert quest_item["grade"] is None


def test_report_card_excludes_quest_assigned_to_someone_else(client, world, cleanup):
    other_student_id, _ = _enroll_new_student(client, world, cleanup)

    quest = _new_quest(client, world, cleanup, assigned_to=other_student_id)

    resp = client.get(f"/api/users/{world.student_id}/report_card", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()

    section = next(s for s in body["sections"] if s["section_id"] == world.section_id)
    quest_ids = {i["item_id"] for i in section["items"] if i["kind"] == "quest"}
    assert quest not in quest_ids


def test_report_card_forbidden_for_teacher(client, world):
    resp = client.get(f"/api/users/{world.student_id}/report_card", headers=auth_header(world.teacher_token))
    assert resp.status_code == 403


def test_report_card_not_found_for_nonexistent_user(client, world):
    resp = client.get("/api/users/999999999/report_card", headers=auth_header(world.admin_token))
    assert resp.status_code == 404


def test_report_card_rejects_non_student_user(client, world):
    resp = client.get(f"/api/users/{world.teacher_id}/report_card", headers=auth_header(world.admin_token))
    assert resp.status_code == 400
