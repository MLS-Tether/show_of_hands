# tests/test_auth.py
from models.user_model import User
from tests.conftest import unique, auth_header


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_and_login_student(client, world, cleanup):
    username = unique("student")
    resp = client.post("/api/auth/register", json={
        "username": username,
        "password": "password123",
        "full_name": "Test Student",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["username"] == username
    assert body["role"] == "student"
    cleanup(User, body["user_id"])

    resp = client.post("/api/auth/login", json={
        "username": username,
        "password": "password123",
    })
    assert resp.status_code == 200, resp.text
    assert "access_token" in resp.json()


def test_register_unknown_school_code(client):
    resp = client.post("/api/auth/register", json={
        "username": unique("nope"),
        "password": "password123",
        "full_name": "Test Student",
        "school_code": "NOT_A_REAL_CODE",
        "role": "student",
    })
    assert resp.status_code == 404


def test_register_duplicate_username_in_school(client, world, cleanup):
    username = unique("dup")
    resp = client.post("/api/auth/register", json={
        "username": username,
        "password": "password123",
        "full_name": "Test Student",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    cleanup(User, resp.json()["user_id"])

    resp = client.post("/api/auth/register", json={
        "username": username,
        "password": "password123",
        "full_name": "Test Student",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 409


def test_teacher_login_blocked_until_verified(client, world, cleanup):
    username = unique("unverified_teacher")
    resp = client.post("/api/auth/register", json={
        "username": username,
        "password": "password123",
        "full_name": "Test Teacher",
        "school_code": world.school_code,
        "role": "teacher",
    })
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["user_id"]
    cleanup(User, user_id)

    resp = client.post("/api/auth/login", json={
        "username": username,
        "password": "password123",
    })
    assert resp.status_code == 403

    resp = client.patch(f"/api/users/{user_id}/verify", headers=auth_header(world.admin_token))
    assert resp.status_code == 200

    resp = client.post("/api/auth/login", json={
        "username": username,
        "password": "password123",
    })
    assert resp.status_code == 200, resp.text


def test_login_wrong_password(client, world):
    resp = client.post("/api/auth/login", json={
        "username": world.student_username,
        "password": "wrong-password",
    })
    assert resp.status_code == 401


def test_refresh_and_logout(client, world, cleanup):
    username = unique("refreshstudent")
    resp = client.post("/api/auth/register", json={
        "username": username,
        "password": "password123",
        "full_name": "Test Student",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    cleanup(User, resp.json()["user_id"])

    resp = client.post("/api/auth/login", json={"username": username, "password": "password123"})
    assert resp.status_code == 200, resp.text
    tokens = resp.json()

    resp = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200, resp.text
    assert "access_token" in resp.json()

    resp = client.post(
        "/api/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=auth_header(tokens["access_token"]),
    )
    assert resp.status_code == 200, resp.text


def test_reset_password_only_for_students(client, world):
    resp = client.post(
        "/api/auth/reset-password",
        json={"user_id": world.teacher_id, "new_password": "newpassword123"},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 403


def test_reset_password_student(client, world, cleanup):
    username = unique("resetme")
    resp = client.post("/api/auth/register", json={
        "username": username,
        "password": "password123",
        "full_name": "Test Student",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["user_id"]
    cleanup(User, user_id)

    resp = client.post(
        "/api/auth/reset-password",
        json={"user_id": user_id, "new_password": "newpassword456"},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = client.post("/api/auth/login", json={
        "username": username,
        "password": "newpassword456",
    })
    assert resp.status_code == 200, resp.text
