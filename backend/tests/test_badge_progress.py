# tests/test_badge_progress.py
from models.badge_rule_model import BadgeRule, BadgeRuleCriteriaEnum
from models.quest_completion_model import QuestCompletion
from tests.conftest import auth_header
from tests.test_report_card import _new_quest
from tests.test_shop import _enroll_new_student, _give_points, _make_shop_item


def _make_badge_rule(db, cleanup, item_id, criteria_type, threshold, params=None):
    rule = BadgeRule(item_id=item_id, criteria_type=criteria_type, threshold=threshold, params=params)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    cleanup(BadgeRule, rule.badge_rule_id)
    return rule


def _complete_quest(client, cleanup, token, quest_id):
    resp = client.post(f"/api/quests/{quest_id}/complete", headers=auth_header(token))
    assert resp.status_code == 201, resp.text
    cleanup(QuestCompletion, resp.json()["quest_completion_id"])


def test_badge_without_rule_has_no_progress(client, world, cleanup):
    badge_id = _make_shop_item(client, world, cleanup, item_type="badge")

    resp = client.get("/api/shop/items?item_type=badge", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    item = next(i for i in resp.json() if i["item_id"] == badge_id)
    assert item["progress"] is None


def test_non_badge_item_has_no_progress(client, world, cleanup, db):
    item_id = _make_shop_item(client, world, cleanup, item_type="avatar_accessory")
    _make_badge_rule(db, cleanup, item_id, BadgeRuleCriteriaEnum.lifetime_points, 100)

    resp = client.get("/api/shop/items", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    item = next(i for i in resp.json() if i["item_id"] == item_id)
    assert item["progress"] is None


def test_badge_progress_quest_total_count(client, world, cleanup, db):
    badge_id = _make_shop_item(client, world, cleanup, item_type="badge")
    _make_badge_rule(db, cleanup, badge_id, BadgeRuleCriteriaEnum.quest_total_count, 5)

    student_id, student_token = _enroll_new_student(client, world, cleanup)
    quest_a = _new_quest(client, world, cleanup)
    quest_b = _new_quest(client, world, cleanup)
    _complete_quest(client, cleanup, student_token, quest_a)
    _complete_quest(client, cleanup, student_token, quest_b)

    resp = client.get("/api/shop/items?item_type=badge", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    item = next(i for i in resp.json() if i["item_id"] == badge_id)
    assert item["progress"] == {"current": 2, "target": 5, "unit": "quests completed"}


def test_badge_progress_lifetime_points(client, world, cleanup, db):
    badge_id = _make_shop_item(client, world, cleanup, item_type="badge")
    _make_badge_rule(db, cleanup, badge_id, BadgeRuleCriteriaEnum.lifetime_points, 500)

    student_id, student_token = _enroll_new_student(client, world, cleanup)
    _give_points(db, student_id, 120)

    resp = client.get("/api/shop/items?item_type=badge", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    item = next(i for i in resp.json() if i["item_id"] == badge_id)
    assert item["progress"] == {"current": 120, "target": 500, "unit": "points"}


def test_badge_progress_hidden_for_teacher(client, world, cleanup, db):
    badge_id = _make_shop_item(client, world, cleanup, item_type="badge")
    _make_badge_rule(db, cleanup, badge_id, BadgeRuleCriteriaEnum.lifetime_points, 500)

    resp = client.get("/api/shop/items?item_type=badge", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    item = next(i for i in resp.json() if i["item_id"] == badge_id)
    assert item.get("progress") is None
