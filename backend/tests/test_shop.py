# tests/test_shop.py
from models.enrollment_model import EnrollmentRequest
from models.inventory_model import InventoryItem
from models.shop_item_model import ShopItem
from models.user_model import User
from tests.conftest import unique, auth_header


def _make_shop_item(client, world, cleanup, item_type="avatar_accessory", cost=10, **overrides):
    body = {
        "name": unique("Item"),
        "description": "A test item",
        "item_type": item_type,
        "cost": cost,
        "image_url": "/shop-placeholders/test.svg",
    }
    body.update(overrides)
    resp = client.post("/api/shop/items", json=body, headers=auth_header(world.admin_token))
    assert resp.status_code == 201, resp.text
    item_id = resp.json()["item_id"]
    cleanup(ShopItem, item_id)
    return item_id


def _enroll_new_student(client, world, cleanup, full_name="Class Mate"):
    username = unique("classmate")
    resp = client.post("/api/auth/register", json={
        "username": username,
        "full_name": full_name,
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

    return user_id, token


def _give_points(db, user_id, amount):
    user = db.query(User).filter(User.user_id == user_id).first()
    user.total_points = amount
    db.commit()


def _give_item_directly(db, cleanup, student_id, item_id):
    """Badges can no longer be purchased, so tests that need one in a
    student's inventory (e.g. to test equip behavior) grant it directly,
    the same way the badge rule engine does."""
    inventory = InventoryItem(student_id=student_id, item_id=item_id, is_equipped=False)
    db.add(inventory)
    db.commit()
    db.refresh(inventory)
    cleanup(InventoryItem, inventory.inventory_id)
    return inventory.inventory_id


def _purchase(client, token, item_id):
    return client.post(f"/api/shop/items/{item_id}/purchase", headers=auth_header(token))


# ---------------------------------------------------------------------------
# GET /shop/items
# ---------------------------------------------------------------------------


def test_list_shop_items_shows_owned_and_equipped_for_student(client, world, cleanup, db):
    owned_item_id = _make_shop_item(client, world, cleanup)
    unowned_item_id = _make_shop_item(client, world, cleanup)
    student_id, student_token = _enroll_new_student(client, world, cleanup)
    _give_points(db, student_id, 1000)

    resp = _purchase(client, student_token, owned_item_id)
    assert resp.status_code == 200, resp.text
    cleanup(InventoryItem, resp.json()["inventory_id"])

    resp = client.get("/api/shop/items", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    by_id = {item["item_id"]: item for item in resp.json()}

    assert by_id[owned_item_id]["owned"] is True
    assert by_id[owned_item_id]["equipped"] is False
    assert by_id[unowned_item_id]["owned"] is False
    assert by_id[unowned_item_id]["equipped"] is False


def test_list_shop_items_hides_owned_equipped_for_teacher_and_admin(client, world, cleanup):
    item_id = _make_shop_item(client, world, cleanup)

    resp = client.get("/api/shop/items", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    item = next(i for i in resp.json() if i["item_id"] == item_id)
    assert item.get("owned") is None
    assert item.get("equipped") is None

    resp = client.get("/api/shop/items", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    item = next(i for i in resp.json() if i["item_id"] == item_id)
    assert item.get("owned") is None


def test_list_shop_items_filters_by_item_type(client, world, cleanup):
    badge_id = _make_shop_item(client, world, cleanup, item_type="badge")
    theme_id = _make_shop_item(client, world, cleanup, item_type="theme", theme_key="ocean")

    resp = client.get("/api/shop/items?item_type=badge", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    ids = {i["item_id"] for i in resp.json()}
    assert badge_id in ids
    assert theme_id not in ids


def test_list_shop_items_invalid_item_type_400(client, world):
    resp = client.get("/api/shop/items?item_type=not_a_real_type", headers=auth_header(world.teacher_token))
    assert resp.status_code == 400


def test_list_shop_items_excludes_archived(client, world, cleanup):
    item_id = _make_shop_item(client, world, cleanup)

    resp = client.delete(f"/api/shop/items/{item_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text

    resp = client.get("/api/shop/items", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    ids = {i["item_id"] for i in resp.json()}
    assert item_id not in ids


# ---------------------------------------------------------------------------
# POST /shop/items (admin create)
# ---------------------------------------------------------------------------


def test_admin_can_create_shop_item(client, world, cleanup):
    item_id = _make_shop_item(client, world, cleanup, item_type="avatar_base", cost=50)
    resp = client.get("/api/shop/items", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    item = next(i for i in resp.json() if i["item_id"] == item_id)
    assert item["cost"] == 50
    assert item["item_type"] == "avatar_base"


def test_teacher_cannot_create_shop_item(client, world):
    resp = client.post(
        "/api/shop/items",
        json={
            "name": unique("Item"),
            "item_type": "badge",
            "cost": 10,
            "image_url": "/shop-placeholders/test.svg",
        },
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 403


def test_student_cannot_create_shop_item(client, world):
    resp = client.post(
        "/api/shop/items",
        json={
            "name": unique("Item"),
            "item_type": "badge",
            "cost": 10,
            "image_url": "/shop-placeholders/test.svg",
        },
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /shop/items/{id}
# ---------------------------------------------------------------------------


def test_admin_can_update_shop_item(client, world, cleanup):
    item_id = _make_shop_item(client, world, cleanup, cost=10)

    resp = client.patch(
        f"/api/shop/items/{item_id}",
        json={"cost": 25},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["cost"] == 25


def test_update_nonexistent_item_404(client, world):
    resp = client.patch(
        "/api/shop/items/999999999",
        json={"cost": 25},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 404


def test_update_archived_item_404(client, world, cleanup):
    item_id = _make_shop_item(client, world, cleanup)
    resp = client.delete(f"/api/shop/items/{item_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text

    resp = client.patch(
        f"/api/shop/items/{item_id}",
        json={"cost": 25},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 404


def test_non_admin_cannot_update_shop_item(client, world, cleanup):
    item_id = _make_shop_item(client, world, cleanup)
    resp = client.patch(
        f"/api/shop/items/{item_id}",
        json={"cost": 25},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /shop/items/{id} (soft delete)
# ---------------------------------------------------------------------------


def test_admin_can_archive_shop_item(client, world, cleanup):
    item_id = _make_shop_item(client, world, cleanup)
    resp = client.delete(f"/api/shop/items/{item_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["message"] == "Shop item archived successfully."


def test_archive_nonexistent_item_404(client, world):
    resp = client.delete("/api/shop/items/999999999", headers=auth_header(world.admin_token))
    assert resp.status_code == 404


def test_non_admin_cannot_archive_shop_item(client, world, cleanup):
    item_id = _make_shop_item(client, world, cleanup)
    resp = client.delete(f"/api/shop/items/{item_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /shop/items/{id}/purchase
# ---------------------------------------------------------------------------


def test_purchase_happy_path(client, world, cleanup, db):
    item_id = _make_shop_item(client, world, cleanup, cost=30)
    student_id, student_token = _enroll_new_student(client, world, cleanup)
    _give_points(db, student_id, 100)

    resp = _purchase(client, student_token, item_id)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["item_id"] == item_id
    assert body["points_spent"] == 30
    assert body["total_points"] == 70
    cleanup(InventoryItem, body["inventory_id"])

    resp = client.get(f"/api/users/{student_id}/inventory", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    inventory = resp.json()
    assert len(inventory) == 1
    assert inventory[0]["item"]["item_id"] == item_id
    assert inventory[0]["is_equipped"] is False

    resp = client.get(f"/api/users/{student_id}/points", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_points"] == 70


def test_purchase_insufficient_points_409(client, world, cleanup, db):
    item_id = _make_shop_item(client, world, cleanup, cost=1000)
    student_id, student_token = _enroll_new_student(client, world, cleanup)
    _give_points(db, student_id, 5)

    resp = _purchase(client, student_token, item_id)
    assert resp.status_code == 409

    resp = client.get(f"/api/users/{student_id}/inventory", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    assert resp.json() == []

    resp = client.get(f"/api/users/{student_id}/points", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_points"] == 5


def test_purchase_already_owned_409(client, world, cleanup, db):
    item_id = _make_shop_item(client, world, cleanup, cost=10)
    student_id, student_token = _enroll_new_student(client, world, cleanup)
    _give_points(db, student_id, 100)

    resp = _purchase(client, student_token, item_id)
    assert resp.status_code == 200, resp.text
    cleanup(InventoryItem, resp.json()["inventory_id"])

    resp = _purchase(client, student_token, item_id)
    assert resp.status_code == 409

    resp = client.get(f"/api/users/{student_id}/points", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_points"] == 90


def test_purchase_nonexistent_item_404(client, world):
    resp = _purchase(client, world.student_token, 999999999)
    assert resp.status_code == 404


def test_purchase_archived_item_404(client, world, cleanup):
    item_id = _make_shop_item(client, world, cleanup)
    resp = client.delete(f"/api/shop/items/{item_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text

    resp = _purchase(client, world.student_token, item_id)
    assert resp.status_code == 404


def test_purchase_badge_403(client, world, cleanup, db):
    badge_id = _make_shop_item(client, world, cleanup, item_type="badge")
    student_id, student_token = _enroll_new_student(client, world, cleanup)
    _give_points(db, student_id, 100)

    resp = _purchase(client, student_token, badge_id)
    assert resp.status_code == 403

    resp = client.get(f"/api/users/{student_id}/inventory", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_teacher_cannot_purchase(client, world, cleanup):
    item_id = _make_shop_item(client, world, cleanup)
    resp = _purchase(client, world.teacher_token, item_id)
    assert resp.status_code == 403


def test_admin_cannot_purchase(client, world, cleanup):
    item_id = _make_shop_item(client, world, cleanup)
    resp = _purchase(client, world.admin_token, item_id)
    assert resp.status_code == 403


def test_purchase_appears_in_points_history_with_label(client, world, cleanup, db):
    item_id = _make_shop_item(client, world, cleanup, cost=15)
    student_id, student_token = _enroll_new_student(client, world, cleanup)
    _give_points(db, student_id, 50)

    resp = _purchase(client, student_token, item_id)
    assert resp.status_code == 200, resp.text
    cleanup(InventoryItem, resp.json()["inventory_id"])

    resp = client.get(f"/api/users/{student_id}/points", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    transactions = resp.json()["transactions"]
    shop_txns = [t for t in transactions if t["source"] == "shop_purchase"]
    assert len(shop_txns) == 1
    assert shop_txns[0]["amount"] == -15
    assert shop_txns[0]["source_id"] == item_id
    assert shop_txns[0]["source_label"] is not None


# ---------------------------------------------------------------------------
# GET /users/{id}/inventory
# ---------------------------------------------------------------------------


def test_student_can_view_own_inventory(client, world):
    resp = client.get(f"/api/users/{world.student_id}/inventory", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)


def test_student_cannot_view_others_inventory(client, world, cleanup):
    other_id, _ = _enroll_new_student(client, world, cleanup)
    resp = client.get(f"/api/users/{other_id}/inventory", headers=auth_header(world.student_token))
    assert resp.status_code == 403


def test_teacher_and_admin_can_view_any_student_inventory_in_school(client, world):
    resp = client.get(f"/api/users/{world.student_id}/inventory", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/users/{world.student_id}/inventory", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text


def test_view_inventory_cross_school_403(client, world, cleanup):
    other_school_name = unique("School")
    other_admin_username = unique("admin")
    resp = client.post("/api/schools", json={
        "school_name": other_school_name,
        "admin_username": other_admin_username,
        "admin_password": "password123",
    })
    assert resp.status_code == 201, resp.text
    other_school = resp.json()
    other_admin_token = other_school["access_token"]

    resp = client.get(f"/api/users/{world.student_id}/inventory", headers=auth_header(other_admin_token))
    assert resp.status_code == 403


def test_view_inventory_nonexistent_user_404(client, world):
    resp = client.get("/api/users/999999999/inventory", headers=auth_header(world.admin_token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /inventory/{id}/equip
# ---------------------------------------------------------------------------


def test_equip_and_unequip_owned_item(client, world, cleanup, db):
    item_id = _make_shop_item(client, world, cleanup, item_type="badge")
    student_id, student_token = _enroll_new_student(client, world, cleanup)

    inventory_id = _give_item_directly(db, cleanup, student_id, item_id)

    resp = client.patch(
        f"/api/inventory/{inventory_id}/equip",
        json={"equipped": True},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_equipped"] is True

    resp = client.patch(
        f"/api/inventory/{inventory_id}/equip",
        json={"equipped": False},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_equipped"] is False


def test_equip_single_equip_type_unequips_sibling(client, world, cleanup, db):
    base_1 = _make_shop_item(client, world, cleanup, item_type="avatar_base")
    base_2 = _make_shop_item(client, world, cleanup, item_type="avatar_base")
    student_id, student_token = _enroll_new_student(client, world, cleanup)
    _give_points(db, student_id, 100)

    resp = _purchase(client, student_token, base_1)
    assert resp.status_code == 200, resp.text
    inv_1 = resp.json()["inventory_id"]
    cleanup(InventoryItem, inv_1)

    resp = _purchase(client, student_token, base_2)
    assert resp.status_code == 200, resp.text
    inv_2 = resp.json()["inventory_id"]
    cleanup(InventoryItem, inv_2)

    resp = client.patch(
        f"/api/inventory/{inv_1}/equip",
        json={"equipped": True},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_equipped"] is True

    resp = client.patch(
        f"/api/inventory/{inv_2}/equip",
        json={"equipped": True},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_equipped"] is True

    resp = client.get(f"/api/users/{student_id}/inventory", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    by_id = {row["inventory_id"]: row for row in resp.json()}
    assert by_id[inv_1]["is_equipped"] is False
    assert by_id[inv_2]["is_equipped"] is True


def test_badges_are_not_single_equip(client, world, cleanup, db):
    badge_1 = _make_shop_item(client, world, cleanup, item_type="badge")
    badge_2 = _make_shop_item(client, world, cleanup, item_type="badge")
    student_id, student_token = _enroll_new_student(client, world, cleanup)

    inv_1 = _give_item_directly(db, cleanup, student_id, badge_1)
    inv_2 = _give_item_directly(db, cleanup, student_id, badge_2)

    for inv_id in (inv_1, inv_2):
        resp = client.patch(
            f"/api/inventory/{inv_id}/equip",
            json={"equipped": True},
            headers=auth_header(student_token),
        )
        assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/users/{student_id}/inventory", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    by_id = {row["inventory_id"]: row for row in resp.json()}
    assert by_id[inv_1]["is_equipped"] is True
    assert by_id[inv_2]["is_equipped"] is True


def test_equip_others_item_403(client, world, cleanup, db):
    item_id = _make_shop_item(client, world, cleanup)
    owner_id, owner_token = _enroll_new_student(client, world, cleanup)
    _, other_token = _enroll_new_student(client, world, cleanup, full_name="Other Student")
    _give_points(db, owner_id, 100)

    resp = _purchase(client, owner_token, item_id)
    assert resp.status_code == 200, resp.text
    inventory_id = resp.json()["inventory_id"]
    cleanup(InventoryItem, inventory_id)

    resp = client.patch(
        f"/api/inventory/{inventory_id}/equip",
        json={"equipped": True},
        headers=auth_header(other_token),
    )
    assert resp.status_code == 403


def test_equip_nonexistent_inventory_404(client, world):
    resp = client.patch(
        "/api/inventory/999999999/equip",
        json={"equipped": True},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 404


def test_non_student_cannot_equip(client, world, cleanup, db):
    item_id = _make_shop_item(client, world, cleanup)
    student_id, student_token = _enroll_new_student(client, world, cleanup)
    _give_points(db, student_id, 100)

    resp = _purchase(client, student_token, item_id)
    assert resp.status_code == 200, resp.text
    inventory_id = resp.json()["inventory_id"]
    cleanup(InventoryItem, inventory_id)

    resp = client.patch(
        f"/api/inventory/{inventory_id}/equip",
        json={"equipped": True},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 403
