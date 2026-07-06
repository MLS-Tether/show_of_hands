# tests/test_sections.py
from models.section_model import Section
from tests.conftest import unique, auth_header


def test_list_sections(client, world):
    resp = client.get("/api/sections", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    sections = resp.json()
    assert any(s["section_id"] == world.section_id for s in sections)

    resp = client.get(f"/api/sections?class_id={world.class_id}", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    assert all(s["class_name"] for s in resp.json())


def test_create_section_requires_teacher(client, world, cleanup):
    resp = client.post("/api/sections", json={
        "class_id": world.class_id,
        "period": unique("Period"),
        "capacity": 20,
    }, headers=auth_header(world.student_token))
    assert resp.status_code == 403

    resp = client.post("/api/sections", json={
        "class_id": world.class_id,
        "period": unique("Period"),
        "capacity": 20,
    }, headers=auth_header(world.teacher_token))
    assert resp.status_code == 201, resp.text
    cleanup(Section, resp.json()["section_id"])


def test_get_section_detail_access_rules(client, world):
    resp = client.get(f"/api/sections/{world.section_id}", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["section_id"] == world.section_id
    assert any(s["user_id"] == world.student_id for s in body["students"])

    resp = client.get(f"/api/sections/{world.section_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/sections/{world.section_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text


def test_get_section_detail_unenrolled_student_forbidden(client, world, cleanup):
    section_resp = client.post("/api/sections", json={
        "class_id": world.class_id,
        "period": unique("Period"),
        "capacity": 20,
    }, headers=auth_header(world.teacher_token))
    assert section_resp.status_code == 201, section_resp.text
    section_id = section_resp.json()["section_id"]
    cleanup(Section, section_id)

    resp = client.get(f"/api/sections/{section_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 403


def test_patch_section_teacher_partial_update(client, world, cleanup):
    section_resp = client.post("/api/sections", json={
        "class_id": world.class_id,
        "period": unique("Period"),
        "capacity": 20,
    }, headers=auth_header(world.teacher_token))
    assert section_resp.status_code == 201, section_resp.text
    section_id = section_resp.json()["section_id"]
    cleanup(Section, section_id)

    resp = client.patch(f"/api/sections/{section_id}", json={"capacity": 40}, headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text

    resp = client.patch(
        f"/api/sections/{section_id}",
        json={"status": "archived"},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] != "archived"


def test_patch_section_students_forbidden(client, world):
    resp = client.patch(
        f"/api/sections/{world.section_id}",
        json={"capacity": 99},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 403


def test_patch_section_admin_can_set_status(client, world, cleanup):
    section_resp = client.post("/api/sections", json={
        "class_id": world.class_id,
        "period": unique("Period"),
        "capacity": 20,
    }, headers=auth_header(world.teacher_token))
    assert section_resp.status_code == 201, section_resp.text
    section_id = section_resp.json()["section_id"]
    cleanup(Section, section_id)

    resp = client.patch(
        f"/api/sections/{section_id}",
        json={"status": "archived"},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "archived"


def test_delete_section_requires_admin(client, world, cleanup):
    section_resp = client.post("/api/sections", json={
        "class_id": world.class_id,
        "period": unique("Period"),
        "capacity": 20,
    }, headers=auth_header(world.teacher_token))
    assert section_resp.status_code == 201, section_resp.text
    section_id = section_resp.json()["section_id"]
    cleanup(Section, section_id)

    resp = client.delete(f"/api/sections/{section_id}", headers=auth_header(world.teacher_token))
    assert resp.status_code == 403

    resp = client.delete(f"/api/sections/{section_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/sections/{section_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 404
