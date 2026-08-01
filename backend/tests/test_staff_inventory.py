# tests/test_staff_inventory.py
from models.school_model import School
from models.user_model import User
from tests.conftest import unique, auth_header
from tests.test_shop import _make_shop_item


def _non_badge_item_ids(client, token):
    resp = client.get("/api/shop/items", headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    return {i["item_id"] for i in resp.json() if i["item_type"] != "badge"}


def _inventory_item_ids(client, token, user_id):
    resp = client.get(f"/api/users/{user_id}/inventory", headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    return {row["item"]["item_id"] for row in resp.json()}


def test_new_teacher_owns_all_existing_cosmetics(client, world, cleanup):
    expected_ids = _non_badge_item_ids(client, world.admin_token)

    resp = client.post("/api/auth/register", json={
        "username": unique("teacher"),
        "password": "password123",
        "full_name": "New Teacher",
        "school_code": world.school_code,
        "role": "teacher",
    })
    assert resp.status_code == 201, resp.text
    teacher_id = resp.json()["user_id"]
    cleanup(User, teacher_id)

    owned_ids = _inventory_item_ids(client, world.admin_token, teacher_id)
    assert owned_ids == expected_ids


def test_new_school_admin_owns_all_existing_cosmetics(client, world, cleanup):
    expected_ids = _non_badge_item_ids(client, world.admin_token)

    resp = client.post("/api/schools", json={
        "school_name": unique("NewSchool"),
        "admin_username": unique("founder"),
        "admin_password": "password123",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    cleanup(School, body["school_id"])
    cleanup(User, body["admin_user_id"])

    owned_ids = _inventory_item_ids(client, body["access_token"], body["admin_user_id"])
    assert owned_ids == expected_ids


def test_new_cosmetic_item_backfilled_to_existing_teacher(client, world, cleanup):
    item_id = _make_shop_item(client, world, cleanup, item_type="theme", theme_key=unique("theme"))

    owned_ids = _inventory_item_ids(client, world.admin_token, world.teacher_id)
    assert item_id in owned_ids


def test_staff_can_equip_auto_unlocked_item(client, world, cleanup):
    item_id = _make_shop_item(client, world, cleanup, item_type="avatar_accessory")

    resp = client.get(f"/api/users/{world.teacher_id}/inventory", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    inventory_id = next(row["inventory_id"] for row in resp.json() if row["item"]["item_id"] == item_id)

    resp = client.patch(
        f"/api/inventory/{inventory_id}/equip",
        json={"equipped": True},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_equipped"] is True


def test_staff_cannot_equip_someone_elses_item(client, world, cleanup):
    resp = client.post("/api/auth/register", json={
        "username": unique("teacher"),
        "password": "password123",
        "full_name": "Other Teacher",
        "school_code": world.school_code,
        "role": "teacher",
    })
    assert resp.status_code == 201, resp.text
    other_teacher_id = resp.json()["user_id"]
    cleanup(User, other_teacher_id)

    resp = client.get(f"/api/users/{other_teacher_id}/inventory", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    inventory_id = resp.json()[0]["inventory_id"]

    resp = client.patch(
        f"/api/inventory/{inventory_id}/equip",
        json={"equipped": True},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 403
