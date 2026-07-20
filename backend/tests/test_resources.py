from models.resource_model import Resource
from models.user_model import User
from tests.conftest import auth_header, unique


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


def test_teacher_updates_resource(client, world, cleanup):
    created = _create_resource(client, world, cleanup)
    rid = created.json()["resource_id"]
    resp = client.patch(
        f"/api/resources/{rid}",
        json={"title": "Updated title", "description": None},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["title"] == "Updated title"


def test_update_rejects_bad_url(client, world, cleanup):
    created = _create_resource(client, world, cleanup)
    rid = created.json()["resource_id"]
    resp = client.patch(
        f"/api/resources/{rid}",
        json={"url": "ftp://example.com"},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 422


def test_student_cannot_update_resource(client, world, cleanup):
    created = _create_resource(client, world, cleanup)
    rid = created.json()["resource_id"]
    resp = client.patch(
        f"/api/resources/{rid}",
        json={"title": "Hacked"},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 403


def test_teacher_deletes_resource(client, world, cleanup):
    created = _create_resource(client, world, cleanup)
    rid = created.json()["resource_id"]
    resp = client.delete(f"/api/resources/{rid}", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200
    # soft-deleted: no longer listed
    listing = client.get(
        f"/api/sections/{world.section_id}/resources",
        headers=auth_header(world.teacher_token),
    )
    assert rid not in [r["resource_id"] for r in listing.json()]


def test_delete_unknown_resource_404(client, world):
    resp = client.delete("/api/resources/999999", headers=auth_header(world.teacher_token))
    assert resp.status_code == 404


def test_teacher_delete_sets_archived_and_deleted_at(client, world, cleanup, db):
    created = _create_resource(client, world, cleanup)
    rid = created.json()["resource_id"]
    resp = client.delete(f"/api/resources/{rid}", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200

    db.expire_all()
    resource = db.query(Resource).filter(Resource.resource_id == rid).first()
    assert resource is not None
    assert resource.is_archived is True
    assert resource.deleted_at is not None


def test_other_teacher_cannot_update_or_delete_resource(client, world, cleanup):
    """A teacher who doesn't own the section should get 403 on both PATCH
    and DELETE of another teacher's resource, mirroring how `world` itself
    registers+verifies+logs in a teacher."""
    created = _create_resource(client, world, cleanup)
    rid = created.json()["resource_id"]

    other_username = unique("teacher2")
    resp = client.post(
        "/api/auth/register",
        json={
            "username": other_username,
            "full_name": "Other Teacher",
            "password": "password123",
            "school_code": world.school_code,
            "role": "teacher",
        },
    )
    assert resp.status_code == 201, resp.text
    other_teacher_id = resp.json()["user_id"]
    cleanup(User, other_teacher_id)

    resp = client.patch(
        f"/api/users/{other_teacher_id}/verify",
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = client.post(
        "/api/auth/login",
        json={"username": other_username, "password": "password123"},
    )
    assert resp.status_code == 200, resp.text
    other_teacher_token = resp.json()["access_token"]

    resp = client.patch(
        f"/api/resources/{rid}",
        json={"title": "Hijacked"},
        headers=auth_header(other_teacher_token),
    )
    assert resp.status_code == 403

    resp = client.delete(f"/api/resources/{rid}", headers=auth_header(other_teacher_token))
    assert resp.status_code == 403
