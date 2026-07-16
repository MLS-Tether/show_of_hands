# tests/test_section_grades.py
from models.assignment_model import Assignment
from models.submission_model import Submission
from models.user_model import User
from tests.conftest import unique, auth_header


def _new_assignment(client, world, cleanup, category, point_value=100, due_date="2027-01-01T00:00:00Z"):
    resp = client.post(
        f"/api/sections/{world.section_id}/assignments",
        json={
            "title": unique("HW"),
            "due_date": due_date,
            "point_value": point_value,
            "category": category,
        },
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    assignment_id = resp.json()["assignment_id"]
    cleanup(Assignment, assignment_id)
    return assignment_id


def _submit(client, world, cleanup, assignment_id):
    resp = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        json={},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    submission_id = resp.json()["submission_id"]
    cleanup(Submission, submission_id)
    return submission_id


def _grade_and_finalize(client, world, submission_id, grade):
    resp = client.patch(
        f"/api/submissions/{submission_id}/grade",
        json={"grade": grade},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/api/submissions/{submission_id}/finalize", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text


def test_student_can_view_own_grade(client, world, cleanup):
    hw = _new_assignment(client, world, cleanup, "homework")
    quiz = _new_assignment(client, world, cleanup, "quizzes")
    sub_hw = _submit(client, world, cleanup, hw)
    sub_quiz = _submit(client, world, cleanup, quiz)
    _grade_and_finalize(client, world, sub_hw, 80)
    _grade_and_finalize(client, world, sub_quiz, 80)

    resp = client.get(f"/api/sections/{world.section_id}/grades/me", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["percentage"] == 80.0
    assert body["letter_grade"] == "B"


def test_no_graded_submissions_returns_nulls(client, world, cleanup):
    _new_assignment(client, world, cleanup, "homework")
    resp = client.get(f"/api/sections/{world.section_id}/grades/me", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["percentage"] is None
    assert body["letter_grade"] is None


def test_owning_teacher_can_view_student_grade(client, world, cleanup):
    hw = _new_assignment(client, world, cleanup, "homework")
    sub = _submit(client, world, cleanup, hw)
    _grade_and_finalize(client, world, sub, 95)

    resp = client.get(
        f"/api/sections/{world.section_id}/grades/{world.student_id}",
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["percentage"] == 95.0
    assert body["letter_grade"] == "A"


def test_admin_can_view_student_grade(client, world):
    resp = client.get(
        f"/api/sections/{world.section_id}/grades/{world.student_id}",
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text


def test_non_owning_teacher_forbidden(client, world, cleanup):
    other_teacher_username = unique("teacher2")
    resp = client.post("/api/auth/register", json={
        "username": other_teacher_username,
        "password": "password123",
        "school_code": world.school_code,
        "role": "teacher",
    })
    assert resp.status_code == 201, resp.text
    other_teacher_id = resp.json()["user_id"]
    cleanup(User, other_teacher_id)

    resp = client.patch(f"/api/users/{other_teacher_id}/verify", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text

    resp = client.post("/api/auth/login", json={
        "username": other_teacher_username,
        "password": "password123",
    })
    assert resp.status_code == 200, resp.text
    other_teacher_token = resp.json()["access_token"]

    resp = client.get(
        f"/api/sections/{world.section_id}/grades/{world.student_id}",
        headers=auth_header(other_teacher_token),
    )
    assert resp.status_code == 403


def test_student_cannot_view_another_students_grade_via_grades_me(client, world):
    # /grades/me is always scoped to the caller -- there is no way to pass
    # another student's id through this route.
    resp = client.get(f"/api/sections/{world.section_id}/grades/me", headers=auth_header(world.student_token))
    assert resp.status_code == 200


def test_teacher_grade_lookup_for_unenrolled_student_404s(client, world, cleanup):
    other_student_username = unique("student2")
    resp = client.post("/api/auth/register", json={
        "username": other_student_username,
        "password": "password123",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    other_student_id = resp.json()["user_id"]
    cleanup(User, other_student_id)

    resp = client.get(
        f"/api/sections/{world.section_id}/grades/{other_student_id}",
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 404
