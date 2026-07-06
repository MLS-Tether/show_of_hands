# tests/test_notifications.py
from tests.conftest import unique, auth_header


def test_notify_section_requires_admin(client, world):
    resp = client.post(
        f"/api/sections/{world.section_id}/notify",
        json={"message": "hello"},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 403


def test_notify_section_fans_out_to_enrolled_students(client, world):
    message = unique("Announcement")
    resp = client.post(
        f"/api/sections/{world.section_id}/notify",
        json={"message": message},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert "1 student" in resp.json()["message"]

    resp = client.get("/api/notifications", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    matching = [n for n in resp.json() if n["message"] == message]
    assert len(matching) == 1
    assert matching[0]["type"] == "section_status"
    assert matching[0]["is_read"] is False


def test_mark_notification_read_cross_user_404(client, world):
    message = unique("PrivateMsg")
    resp = client.post(
        f"/api/sections/{world.section_id}/notify",
        json={"message": message},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = client.get("/api/notifications", headers=auth_header(world.student_token))
    notification_id = [n for n in resp.json() if n["message"] == message][0]["notification_id"]

    resp = client.patch(f"/api/notifications/{notification_id}/read", headers=auth_header(world.teacher_token))
    assert resp.status_code == 404

    resp = client.patch(f"/api/notifications/{notification_id}/read", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_read"] is True


def test_mark_all_notifications_read(client, world):
    for _ in range(2):
        resp = client.post(
            f"/api/sections/{world.section_id}/notify",
            json={"message": unique("Bulk")},
            headers=auth_header(world.admin_token),
        )
        assert resp.status_code == 200, resp.text

    resp = client.patch("/api/notifications/read-all", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text

    resp = client.get("/api/notifications?is_read=false", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    assert resp.json() == []
