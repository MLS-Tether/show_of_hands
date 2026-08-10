# tests/test_analytics.py
from db.pool import SessionLocal
from models.assignment_model import Assignment
from models.enrollment_model import Enrollment, EnrollmentRequest
from models.help_request_model import HelpRequest, HelpRequestAcceptance
from models.quest_model import Quest
from models.quest_completion_model import QuestCompletion
from models.study_room_model import StudyRoom, RoomMember
from models.submission_model import Submission
from models.user_model import User
from tests.conftest import unique, auth_header


def _new_quest(client, world, cleanup, point_value=15, category="academic"):
    resp = client.post(
        f"/api/sections/{world.section_id}/quests",
        json={
            "title": unique("Quest"),
            "description": "d",
            "category": category,
            "point_value": point_value,
            "quest_type": "daily",
            "assigned_to": "all",
        },
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    cleanup(Quest, body["quest_id"])
    return body["quest_id"], body["point_value"]


def _enroll_new_student(client, world, cleanup):
    username = unique("classmate")
    resp = client.post("/api/auth/register", json={
        "username": username,
        "full_name": "Class Mate",
        "password": "password123",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["user_id"]
    cleanup(User, user_id)

    resp = client.post("/api/auth/login", json={"username": username, "password": "password123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]

    resp = client.post(f"/api/sections/{world.section_id}/enrollment-requests", headers=auth_header(token))
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["enrollment_request_id"]
    cleanup(EnrollmentRequest, request_id)

    resp = client.patch(
        f"/api/enrollment-requests/{request_id}",
        json={"status": "accepted"},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text

    db = SessionLocal()
    enrollment = db.query(Enrollment).filter(
        Enrollment.section_id == world.section_id,
        Enrollment.student_id == user_id,
    ).first()
    enrollment_id = enrollment.enrollment_id
    db.close()
    cleanup(Enrollment, enrollment_id)

    return user_id, username, token


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


def _submit(client, world, cleanup, assignment_id, student_token=None):
    resp = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        json={},
        headers=auth_header(student_token or world.student_token),
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


def test_analytics_ignores_dropped_student(client, world, cleanup):
    classmate_id, _classmate_username, classmate_token = _enroll_new_student(client, world, cleanup)

    # An assignment created *after* the drop below still needs to reflect
    # only currently-enrolled students -- due in the future so it doesn't
    # also trigger a no_submission flag for world.student, keeping this
    # test focused on the completion_rate/attention-scoping bug alone.
    a1 = _new_assignment(client, world, cleanup, point_value=100)
    sub1 = _submit(client, world, cleanup, a1, classmate_token)
    _grade_and_finalize(client, world, sub1, 50)  # below LOW_GRADE_THRESHOLD

    resp = client.delete(
        f"/api/sections/{world.section_id}/students/{classmate_id}",
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/sections/{world.section_id}/analytics", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()

    by_id = {a["assignment_id"]: a for a in body["assignments"]}
    # Before the fix this was 1 (the dropped student's submission still
    # counted) against an enrolled_count that had already dropped to 1
    # (world.student only) -- completion_rate came out to 100% even though
    # no *currently enrolled* student had submitted anything.
    assert by_id[a1]["submitted_count"] == 0
    assert by_id[a1]["completion_rate"] == 0.0

    attention_user_ids = {s["user_id"] for s in body["students_needing_attention"]}
    assert classmate_id not in attention_user_ids


def test_analytics_average_grade_matches_weighted_formula(client, world, cleanup):
    # One graded assignment (100) and one overdue assignment never submitted
    # -- grading.py counts a true non-submission as a 0 in its category, so
    # the correct section average (both assignments default to the
    # "homework" category, weight renormalized to 1.0 since it's the only
    # category present) is mean([100, 0]) = 50, not a flat mean of only the
    # graded grade (which would incorrectly read 100).
    a1 = _new_assignment(client, world, cleanup, point_value=100)
    sub1 = _submit(client, world, cleanup, a1, world.student_token)
    _grade_and_finalize(client, world, sub1, 100)

    _new_assignment(client, world, cleanup, point_value=50, due_date="2020-01-01T00:00:00Z")

    resp = client.get(f"/api/sections/{world.section_id}/analytics", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["average_grade"] == 50


def test_analytics_shows_study_room_activity(client, world, cleanup):
    classmate_id, classmate_username, classmate_token = _enroll_new_student(client, world, cleanup)

    resp = client.post(
        f"/api/sections/{world.section_id}/help-requests",
        json={"topic": "Analytics room test", "group_size": 2, "duration_minutes": 30},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    hr_id = resp.json()["help_request_id"]
    cleanup(HelpRequest, hr_id)

    resp = client.post(f"/api/help-requests/{hr_id}/accept", headers=auth_header(classmate_token))
    assert resp.status_code == 200, resp.text
    room_id = resp.json()["room_id"]
    cleanup(StudyRoom, room_id)
    cleanup(RoomMember, room_id=room_id, user_id=world.student_id)
    cleanup(RoomMember, room_id=room_id, user_id=classmate_id)
    cleanup(HelpRequestAcceptance, help_request_id=hr_id, user_id=classmate_id)

    resp = client.get(f"/api/sections/{world.section_id}/analytics", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()

    rooms_by_id = {r["room_id"]: r for r in body["study_rooms"]}
    room = rooms_by_id[room_id]
    assert room["topic"] == "Analytics room test"
    assert room["requester_id"] == world.student_id
    assert room["requester_username"] == world.student_username
    assert room["status"] == "active"
    member_usernames = {m["username"] for m in room["members"]}
    assert member_usernames == {world.student_username, classmate_username}
    assert body["study_rooms_page"] == 1
    assert body["study_rooms_total_rooms"] >= 1


def test_analytics_includes_quest_completion_stats(client, world, cleanup):
    completed_quest, completed_quest_points = _new_quest(client, world, cleanup, point_value=15, category="social")
    uncompleted_quest, _uncompleted_quest_points = _new_quest(client, world, cleanup, point_value=20, category="academic")

    resp = client.post(
        f"/api/quests/{completed_quest}/complete",
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 201, resp.text
    cleanup(QuestCompletion, resp.json()["quest_completion_id"])

    resp = client.get(f"/api/sections/{world.section_id}/analytics", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["quest_count"] >= 2
    by_id = {q["quest_id"]: q for q in body["quests"]}
    assert by_id[completed_quest]["category"] == "social"
    assert by_id[completed_quest]["point_value"] == completed_quest_points
    assert by_id[completed_quest]["completed_count"] == 1
    assert by_id[completed_quest]["completion_rate"] == 1.0 / body["enrolled_count"]
    assert by_id[uncompleted_quest]["completed_count"] == 0
    assert by_id[uncompleted_quest]["completion_rate"] == 0.0


def test_analytics_quest_stats_ignore_dropped_student(client, world, cleanup):
    classmate_id, _classmate_username, classmate_token = _enroll_new_student(client, world, cleanup)

    quest_id, _quest_points = _new_quest(client, world, cleanup, point_value=10)
    resp = client.post(f"/api/quests/{quest_id}/complete", headers=auth_header(classmate_token))
    assert resp.status_code == 201, resp.text
    cleanup(QuestCompletion, resp.json()["quest_completion_id"])

    resp = client.delete(
        f"/api/sections/{world.section_id}/students/{classmate_id}",
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/sections/{world.section_id}/analytics", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()

    by_id = {q["quest_id"]: q for q in body["quests"]}
    assert by_id[quest_id]["completed_count"] == 0


def test_analytics_study_rooms_paginated(client, world, cleanup):
    resp = client.get(
        f"/api/sections/{world.section_id}/analytics",
        params={"rooms_page": 1, "rooms_page_size": 1},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["study_rooms_page"] == 1
    assert body["study_rooms_page_size"] == 1
    assert len(body["study_rooms"]) <= 1
