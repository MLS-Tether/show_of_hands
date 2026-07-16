# tests/test_schools.py
from models.school_model import School
from models.user_model import User
from tests.conftest import unique, auth_header


def test_create_school(client, cleanup):
    school_name = unique("NewSchool")
    admin_username = unique("founder")
    resp = client.post("/api/schools", json={
        "school_name": school_name,
        "admin_username": admin_username,
        "admin_password": "password123",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == school_name
    assert body["admin_username"] == admin_username
    assert body["school_code"]
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"
    cleanup(School, body["school_id"])
    cleanup(User, body["admin_user_id"])


def test_create_school_duplicate_name(client, cleanup):
    school_name = unique("DupSchool")
    resp = client.post("/api/schools", json={
        "school_name": school_name,
        "admin_username": unique("founder"),
        "admin_password": "password123",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    cleanup(School, body["school_id"])
    cleanup(User, body["admin_user_id"])

    resp = client.post("/api/schools", json={
        "school_name": school_name,
        "admin_username": unique("founder2"),
        "admin_password": "password123",
    })
    assert resp.status_code == 409


def test_get_school_code_requires_admin(client, world):
    resp = client.get("/api/schools/code", headers=auth_header(world.teacher_token))
    assert resp.status_code == 403

    resp = client.get("/api/schools/code", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["school_code"] == world.school_code


def test_get_my_school(client, world):
    for token in (world.admin_token, world.teacher_token, world.student_token):
        resp = client.get("/api/schools/me", headers=auth_header(token))
        assert resp.status_code == 200, resp.text
        assert resp.json()["school_id"] == world.school_id


def test_update_my_school_requires_admin(client, world):
    resp = client.patch(
        "/api/schools/me",
        json={"district": "NYC Geographic District 1"},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 403


def test_update_my_school(client, world):
    resp = client.patch(
        "/api/schools/me",
        json={"district": "NYC Geographic District 1", "grades": "9-12"},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["district"] == "NYC Geographic District 1"
    assert body["grades"] == "9-12"

    resp = client.get("/api/schools/me", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["district"] == "NYC Geographic District 1"
    assert resp.json()["grades"] == "9-12"


def test_get_school_points_requires_admin(client, world):
    resp = client.get("/api/schools/points", headers=auth_header(world.teacher_token))
    assert resp.status_code == 403

    resp = client.get("/api/schools/points", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json()["total_points"], int)
