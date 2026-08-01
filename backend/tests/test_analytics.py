# tests/test_analytics.py
from models.assignment_model import Assignment
from models.submission_model import Submission
from models.user_model import User
from tests.conftest import unique, auth_header


def _new_assignment(client, world, cleanup, point_value=100, due_date="2027-01-01T00:00:00Z"):
    resp = client.post(
        f"/api/sections/{world.section_id}/assignments",
        json={"title": unique("HW"), "due_date": due_date, "point_value": point_value},
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
    return resp.json()


def test_analytics_computes_expected_numbers(client, world, cleanup):
    # Assignment 1: one submission graded high (90), one ungraded left as "submitted".
    a1 = _new_assignment(client, world, cleanup, point_value=100)
    sub1 = _submit(client, world, cleanup, a1)
    _grade_and_finalize(client, world, sub1, 90)

    # Assignment 2: due in the past, no submissions -> flags the enrolled student.
    a2 = _new_assignment(client, world, cleanup, point_value=50, due_date="2020-01-01T00:00:00Z")

    resp = client.get(f"/api/sections/{world.section_id}/analytics", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["section_id"] == world.section_id
    assert body["enrolled_count"] >= 1
    assert body["assignment_count"] >= 2

    by_id = {a["assignment_id"]: a for a in body["assignments"]}
    assert by_id[a1]["submitted_count"] == 1
    assert by_id[a1]["graded_count"] == 1
    assert by_id[a1]["average_grade"] == 90
    assert by_id[a2]["submitted_count"] == 0
    assert by_id[a2]["graded_count"] == 0
    assert by_id[a2]["average_grade"] is None
    assert by_id[a2]["completion_rate"] == 0.0

    attention = body["students_needing_attention"]
    assert any(
        student["user_id"] == world.student_id
        and any(i["assignment_id"] == a2 and i["reason"] == "no_submission" for i in student["issues"])
        for student in attention
    )


def test_analytics_flags_low_grade(client, world, cleanup):
    a1 = _new_assignment(client, world, cleanup, point_value=100)
    sub1 = _submit(client, world, cleanup, a1)
    _grade_and_finalize(client, world, sub1, 50)

    resp = client.get(f"/api/sections/{world.section_id}/analytics", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    attention = resp.json()["students_needing_attention"]
    assert any(
        any(i["assignment_id"] == a1 and i["reason"] == "low_grade" and i["grade"] == 50 for i in student["issues"])
        for student in attention
    )


def test_analytics_attention_paginated_by_student(client, world, cleanup):
    # Two overdue assignments with no submissions -> the one enrolled student
    # is flagged twice, but should appear once, grouped, with both issues.
    a1 = _new_assignment(client, world, cleanup, point_value=50, due_date="2020-01-01T00:00:00Z")
    a2 = _new_assignment(client, world, cleanup, point_value=50, due_date="2020-01-01T00:00:00Z")

    resp = client.get(
        f"/api/sections/{world.section_id}/analytics",
        params={"attention_page": 1, "attention_page_size": 1},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["attention_page"] == 1
    assert body["attention_page_size"] == 1
    assert body["attention_total_students"] == 1
    assert body["attention_total_pages"] == 1
    assert len(body["students_needing_attention"]) == 1

    student = body["students_needing_attention"][0]
    assert student["user_id"] == world.student_id
    flagged_assignment_ids = {i["assignment_id"] for i in student["issues"]}
    assert flagged_assignment_ids == {a1, a2}


def test_analytics_forbidden_for_student(client, world):
    resp = client.get(f"/api/sections/{world.section_id}/analytics", headers=auth_header(world.student_token))
    assert resp.status_code == 403


def test_analytics_forbidden_for_non_owning_teacher(client, world, cleanup):
    other_teacher_username = unique("teacher2")
    resp = client.post("/api/auth/register", json={
        "username": other_teacher_username,
        "password": "password123",
        "full_name": "Test Teacher",
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

    resp = client.get(f"/api/sections/{world.section_id}/analytics", headers=auth_header(other_teacher_token))
    assert resp.status_code == 403


def test_analytics_not_found(client, world):
    resp = client.get("/api/sections/999999999/analytics", headers=auth_header(world.teacher_token))
    assert resp.status_code == 404
