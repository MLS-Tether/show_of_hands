# tests/test_class_requests.py
from models.class_request_model import ClassRequest
from models.class__model import Class_
from tests.conftest import unique, auth_header


def test_create_class_request_requires_teacher(client, world):
    resp = client.post(
        "/api/class-requests",
        json={"class_name": unique("NewClass")},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 403


def test_create_and_list_class_requests(client, world, cleanup):
    class_name = unique("NewClass")
    resp = client.post(
        "/api/class-requests",
        json={"class_name": class_name},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["class_name"] == class_name
    assert body["status"] == "pending"
    cleanup(ClassRequest, body["class_request_id"])

    resp = client.get("/api/class-requests", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    assert any(r["class_request_id"] == body["class_request_id"] for r in resp.json())

    resp = client.get("/api/class-requests", headers=auth_header(world.teacher_token))
    assert resp.status_code == 403


def test_approve_class_request_creates_class(client, world, cleanup):
    class_name = unique("ApprovedClass")
    resp = client.post(
        "/api/class-requests",
        json={"class_name": class_name},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["class_request_id"]
    cleanup(ClassRequest, request_id)

    resp = client.patch(
        f"/api/class-requests/{request_id}",
        json={"status": "approved"},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "approved"

    resp = client.get("/api/classes", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    matching = [c for c in resp.json() if c["name"] == class_name]
    assert len(matching) == 1
    cleanup(Class_, matching[0]["class_id"])


def test_reject_class_request(client, world, cleanup):
    class_name = unique("RejectedClass")
    resp = client.post(
        "/api/class-requests",
        json={"class_name": class_name},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["class_request_id"]
    cleanup(ClassRequest, request_id)

    resp = client.patch(
        f"/api/class-requests/{request_id}",
        json={"status": "rejected"},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"


def test_class_request_cannot_be_processed_twice(client, world, cleanup):
    class_name = unique("OnceOnly")
    resp = client.post(
        "/api/class-requests",
        json={"class_name": class_name},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["class_request_id"]
    cleanup(ClassRequest, request_id)

    resp = client.patch(
        f"/api/class-requests/{request_id}",
        json={"status": "rejected"},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = client.patch(
        f"/api/class-requests/{request_id}",
        json={"status": "approved"},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 409
