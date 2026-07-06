# tests/test_assignments.py
from models.assignment_model import Assignment
from tests.conftest import unique, auth_header


def _due_date():
    return "2027-01-01T00:00:00Z"


def test_create_assignment_requires_teacher_owner(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/assignments",
        json={"title": unique("HW"), "due_date": _due_date(), "point_value": 100},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 403

    title = unique("HW")
    resp = client.post(
        f"/api/sections/{world.section_id}/assignments",
        json={"title": title, "due_date": _due_date(), "point_value": 100},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == title
    assert body["section_id"] == world.section_id
    cleanup(Assignment, body["assignment_id"])


def test_list_assignments_access_rules(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/assignments",
        json={"title": unique("HW"), "due_date": _due_date(), "point_value": 50},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    assignment_id = resp.json()["assignment_id"]
    cleanup(Assignment, assignment_id)

    resp = client.get(f"/api/sections/{world.section_id}/assignments", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    assert any(a["assignment_id"] == assignment_id for a in resp.json())

    resp = client.get(f"/api/sections/{world.section_id}/assignments", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text


def test_get_assignment_detail(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/assignments",
        json={"title": unique("HW"), "due_date": _due_date(), "point_value": 50},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    assignment_id = resp.json()["assignment_id"]
    cleanup(Assignment, assignment_id)

    resp = client.get(f"/api/assignments/{assignment_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/assignments/{assignment_id}", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text


def test_patch_assignment_requires_owner_teacher(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/assignments",
        json={"title": unique("HW"), "due_date": _due_date(), "point_value": 50},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    assignment_id = resp.json()["assignment_id"]
    cleanup(Assignment, assignment_id)

    resp = client.patch(
        f"/api/assignments/{assignment_id}",
        json={"point_value": 75},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 403

    resp = client.patch(
        f"/api/assignments/{assignment_id}",
        json={"point_value": 75},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["point_value"] == 75


def test_delete_assignment_teacher_and_admin(client, world, cleanup):
    resp = client.post(
        f"/api/sections/{world.section_id}/assignments",
        json={"title": unique("HW"), "due_date": _due_date(), "point_value": 50},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    assignment_id = resp.json()["assignment_id"]
    cleanup(Assignment, assignment_id)

    resp = client.delete(f"/api/assignments/{assignment_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 403

    resp = client.delete(f"/api/assignments/{assignment_id}", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/assignments/{assignment_id}", headers=auth_header(world.teacher_token))
    assert resp.status_code == 404
