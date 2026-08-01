# tests/test_featured_badge.py
from tests.conftest import auth_header
from tests.test_shop import _enroll_new_student, _give_item_directly, _make_shop_item


def test_set_and_clear_featured_badge(client, world, cleanup, db):
    badge_id = _make_shop_item(client, world, cleanup, item_type="badge")
    student_id, student_token = _enroll_new_student(client, world, cleanup)
    _give_item_directly(db, cleanup, student_id, badge_id)

    resp = client.patch(
        "/api/users/me/featured-badge",
        json={"item_id": badge_id},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["featured_badge"]["item_id"] == badge_id

    resp = client.get(f"/api/users/{student_id}", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["featured_badge"]["item_id"] == badge_id

    resp = client.patch(
        "/api/users/me/featured-badge",
        json={"item_id": None},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["featured_badge"] is None


def test_cannot_feature_unowned_badge(client, world, cleanup):
    badge_id = _make_shop_item(client, world, cleanup, item_type="badge")
    _, student_token = _enroll_new_student(client, world, cleanup)

    resp = client.patch(
        "/api/users/me/featured-badge",
        json={"item_id": badge_id},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 403


def test_cannot_feature_non_badge_item(client, world, cleanup, db):
    item_id = _make_shop_item(client, world, cleanup, item_type="avatar_accessory")
    student_id, student_token = _enroll_new_student(client, world, cleanup)
    _give_item_directly(db, cleanup, student_id, item_id)

    resp = client.patch(
        "/api/users/me/featured-badge",
        json={"item_id": item_id},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 400


def test_featured_badge_nonexistent_item_404(client, world):
    resp = client.patch(
        "/api/users/me/featured-badge",
        json={"item_id": 999999999},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 404


def test_teacher_cannot_set_featured_badge(client, world, cleanup):
    badge_id = _make_shop_item(client, world, cleanup, item_type="badge")

    resp = client.patch(
        "/api/users/me/featured-badge",
        json={"item_id": badge_id},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 403
