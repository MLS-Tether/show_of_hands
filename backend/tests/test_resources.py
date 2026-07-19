from models.resource_model import Resource
from tests.conftest import auth_header


def _create_resource(client, world, cleanup, **overrides):
    body = {
        "title": "Khan Academy: Quadratics",
        "url": "https://www.khanacademy.org/math/algebra/quadratics",
        "description": "Video series on factoring and graphing.",
    }
    body.update(overrides)
    resp = client.post(
        f"/api/sections/{world.section_id}/resources",
        json=body,
        headers=auth_header(world.teacher_token),
    )
    if resp.status_code == 201:
        cleanup(Resource, resp.json()["resource_id"])
    return resp


def test_teacher_creates_resource(client, world, cleanup):
    resp = _create_resource(client, world, cleanup)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["title"] == "Khan Academy: Quadratics"
    assert data["url"].startswith("https://")
    assert data["section_id"] == world.section_id
    assert data["teacher_id"] == world.teacher_id


def test_student_cannot_create_resource(client, world):
    resp = client.post(
        f"/api/sections/{world.section_id}/resources",
        json={"title": "T", "url": "https://example.com"},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 403


def test_invalid_url_scheme_rejected(client, world, cleanup):
    resp = _create_resource(client, world, cleanup, url="javascript:alert(1)")
    assert resp.status_code == 422


def test_enrolled_student_lists_resources(client, world, cleanup):
    created = _create_resource(client, world, cleanup)
    assert created.status_code == 201
    resp = client.get(
        f"/api/sections/{world.section_id}/resources",
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 200, resp.text
    ids = [r["resource_id"] for r in resp.json()]
    assert created.json()["resource_id"] in ids


def test_admin_can_list_resources(client, world, cleanup):
    _create_resource(client, world, cleanup)
    resp = client.get(
        f"/api/sections/{world.section_id}/resources",
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200


def test_list_unknown_section_404(client, world):
    resp = client.get(
        "/api/sections/999999/resources",
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 404
