# tests/test_classes.py
from tests.conftest import auth_header


def test_list_classes_requires_teacher_or_admin(client, world):
    resp = client.get("/api/classes", headers=auth_header(world.student_token))
    assert resp.status_code == 403

    resp = client.get("/api/classes", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    classes = resp.json()
    assert isinstance(classes, list)
    assert len(classes) > 0
    assert {"class_id", "name"} <= classes[0].keys()

    resp = client.get("/api/classes", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
