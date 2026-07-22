# tests/test_submissions.py
import pytest
from sqlalchemy.exc import IntegrityError

from models.assignment_model import Assignment
from models.point_transaction_model import PointTransaction, TransactionSourceEnum
from models.submission_model import Submission
from tests.conftest import unique, auth_header


def _new_assignment(client, world, cleanup, point_value=100):
    resp = client.post(
        f"/api/sections/{world.section_id}/assignments",
        json={"title": unique("HW"), "due_date": "2027-01-01T00:00:00Z", "point_value": point_value},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    assignment_id = resp.json()["assignment_id"]
    cleanup(Assignment, assignment_id)
    return assignment_id


def test_create_submission_awards_initial_points(client, world, cleanup, db):
    assignment_id = _new_assignment(client, world, cleanup, point_value=100)

    resp = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        json={"content": "my work"},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "submitted"
    assert body["points_awarded"] == 25
    cleanup(Submission, body["submission_id"])


def test_create_submission_duplicate_conflict(client, world, cleanup):
    assignment_id = _new_assignment(client, world, cleanup)

    resp = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        json={},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    cleanup(Submission, resp.json()["submission_id"])

    resp = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        json={},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 409


def test_grade_out_of_bounds_rejected(client, world, cleanup):
    assignment_id = _new_assignment(client, world, cleanup)
    resp = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        json={},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    submission_id = resp.json()["submission_id"]
    cleanup(Submission, submission_id)

    resp = client.patch(
        f"/api/submissions/{submission_id}/grade",
        json={"grade": 925},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 422


def test_duplicate_submission_blocked_at_db_level(client, world, cleanup, db):
    assignment_id = _new_assignment(client, world, cleanup)
    resp = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        json={},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    submission_id = resp.json()["submission_id"]
    cleanup(Submission, submission_id)

    # The application-level check-then-insert in create_submission can race;
    # this confirms the DB-level unique constraint backstops it regardless.
    # try/finally (not just rollback after) so a failed assertion here still
    # leaves the shared `db` session clean for this test's own cleanup.
    db.add(Submission(assignment_id=assignment_id, student_id=world.student_id))
    try:
        with pytest.raises(IntegrityError):
            db.flush()
    finally:
        db.rollback()


def test_list_submissions_teacher_admin_only(client, world, cleanup):
    assignment_id = _new_assignment(client, world, cleanup)
    resp = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        json={},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    submission_id = resp.json()["submission_id"]
    cleanup(Submission, submission_id)

    resp = client.get(f"/api/assignments/{assignment_id}/submissions", headers=auth_header(world.student_token))
    assert resp.status_code == 403

    resp = client.get(f"/api/assignments/{assignment_id}/submissions", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    assert any(s["submission_id"] == submission_id for s in resp.json())


def test_grade_and_finalize_submission_high_grade_bonus(client, world, cleanup, db):
    assignment_id = _new_assignment(client, world, cleanup, point_value=100)
    resp = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        json={},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    submission_id = resp.json()["submission_id"]
    cleanup(Submission, submission_id)

    resp = client.patch(
        f"/api/submissions/{submission_id}/grade",
        json={"grade": 90},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "pending"

    resp = client.post(f"/api/submissions/{submission_id}/finalize", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "graded"
    # 25 initial (25% of 100) + 75 bonus (75% of 100, grade >= 85) = 100
    assert body["points_awarded"] == 100

    # the initial 25% transaction is replaced in place, not appended to
    txns = db.query(PointTransaction).filter(
        PointTransaction.user_id == world.student_id,
        PointTransaction.source == TransactionSourceEnum.assignment,
        PointTransaction.source_id == assignment_id,
    ).all()
    assert len(txns) == 1
    assert txns[0].amount == 100


def test_finalize_without_grade_fails(client, world, cleanup):
    assignment_id = _new_assignment(client, world, cleanup)
    resp = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        json={},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    submission_id = resp.json()["submission_id"]
    cleanup(Submission, submission_id)

    resp = client.post(f"/api/submissions/{submission_id}/finalize", headers=auth_header(world.teacher_token))
    assert resp.status_code == 400


def test_grade_already_finalized_conflict(client, world, cleanup):
    assignment_id = _new_assignment(client, world, cleanup)
    resp = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        json={},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    submission_id = resp.json()["submission_id"]
    cleanup(Submission, submission_id)

    resp = client.patch(
        f"/api/submissions/{submission_id}/grade",
        json={"grade": 60},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/api/submissions/{submission_id}/finalize", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text

    resp = client.patch(
        f"/api/submissions/{submission_id}/grade",
        json={"grade": 70},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 409
