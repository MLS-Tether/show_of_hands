# tests/test_points.py
from tests.conftest import auth_header


def test_student_can_view_own_points(client, world):
    resp = client.get(f"/api/users/{world.student_id}/points", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user_id"] == world.student_id
    assert "total_points" in body
    assert isinstance(body["transactions"], list)
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert "total_count" in body


def test_points_pagination_page_size(client, world):
    resp = client.get(
        f"/api/users/{world.student_id}/points?page=1&page_size=1",
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert len(body["transactions"]) <= 1


def test_student_cannot_view_others_points(client, world):
    resp = client.get(f"/api/users/{world.teacher_id}/points", headers=auth_header(world.student_token))
    assert resp.status_code == 403


def test_teacher_and_admin_can_view_any_points(client, world):
    resp = client.get(f"/api/users/{world.student_id}/points", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/users/{world.student_id}/points", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
