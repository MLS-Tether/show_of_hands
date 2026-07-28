# tests/test_users.py
from db.pool import SessionLocal
from models.user_model import User
from models.section_model import Section
from models.enrollment_model import Enrollment, EnrollmentRequest
from models.notification_model import Notification
from tests.conftest import unique, auth_header


def test_list_users_role_filter(client, world):
    resp = client.get("/api/users", headers=auth_header(world.teacher_token))
    assert resp.status_code == 403

    resp = client.get("/api/users?role=student", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    assert all(u["role"] == "student" for u in resp.json())
    assert any(u["user_id"] == world.student_id for u in resp.json())

    resp = client.get("/api/users?role=bogus", headers=auth_header(world.admin_token))
    assert resp.status_code == 400


def test_get_user_self_and_role_rules(client, world):
    resp = client.get(f"/api/users/{world.student_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/users/{world.teacher_id}", headers=auth_header(world.student_token))
    assert resp.status_code == 403

    resp = client.get(f"/api/users/{world.student_id}", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/users/{world.student_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text


def test_verify_user(client, world, cleanup):
    username = unique("needsverify")
    resp = client.post("/api/auth/register", json={
        "username": username,
        "full_name": "Needs Verify",
        "password": "password123",
        "school_code": world.school_code,
        "role": "teacher",
    })
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["user_id"]
    cleanup(User, user_id)

    resp = client.get(f"/api/users/{user_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text

    resp = client.patch(f"/api/users/{user_id}/verify", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text


def test_reject_signup(client, world, cleanup):
    username = unique("rejectme")
    resp = client.post("/api/auth/register", json={
        "username": username,
        "full_name": "Reject Me",
        "password": "password123",
        "school_code": world.school_code,
        "role": "teacher",
    })
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["user_id"]
    cleanup(User, user_id)

    resp = client.patch(
        f"/api/users/{user_id}/reject",
        json={"reason": "Not affiliated with this school."},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/users?role=teacher", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    rejected = next(u for u in resp.json() if u["user_id"] == user_id)
    assert rejected["rejection_reason"] == "Not affiliated with this school."
    assert rejected["is_verified"] is False

    resp = client.post("/api/auth/login", json={"username": username, "password": "password123"})
    assert resp.status_code == 403

    resp = client.patch(f"/api/users/{user_id}/verify", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    resp = client.patch(
        f"/api/users/{user_id}/reject",
        json={},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 409


def test_deactivate_and_reactivate_user(client, world, cleanup):
    username = unique("togglable")
    resp = client.post("/api/auth/register", json={
        "username": username,
        "full_name": "Toggle Able",
        "password": "password123",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["user_id"]
    cleanup(User, user_id)

    resp = client.post("/api/auth/login", json={"username": username, "password": "password123"})
    assert resp.status_code == 200, resp.text
    user_token = resp.json()["access_token"]

    resp = client.patch(f"/api/users/{user_id}/deactivate", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/users/{user_id}", headers=auth_header(user_token))
    assert resp.status_code == 403

    resp = client.post("/api/auth/login", json={"username": username, "password": "password123"})
    assert resp.status_code == 403

    resp = client.patch(f"/api/users/{user_id}/reactivate", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text

    resp = client.post("/api/auth/login", json={"username": username, "password": "password123"})
    assert resp.status_code == 200, resp.text


def test_delete_own_account_forbidden(client, world):
    resp = client.delete(f"/api/users/{world.admin_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 400


def test_deactivate_own_account_forbidden(client, world):
    resp = client.patch(f"/api/users/{world.admin_id}/deactivate", headers=auth_header(world.admin_token))
    assert resp.status_code == 400


def test_delete_teacher_cascades_sections_to_pending_reassignment(client, world, cleanup):
    teacher_username = unique("droppedteacher")
    resp = client.post("/api/auth/register", json={
        "username": teacher_username,
        "full_name": "Dropped Teacher",
        "password": "password123",
        "school_code": world.school_code,
        "role": "teacher",
    })
    assert resp.status_code == 201, resp.text
    teacher_id = resp.json()["user_id"]
    cleanup(User, teacher_id)
    resp = client.patch(f"/api/users/{teacher_id}/verify", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    resp = client.post("/api/auth/login", json={"username": teacher_username, "password": "password123"})
    assert resp.status_code == 200, resp.text
    teacher_token = resp.json()["access_token"]

    resp = client.post("/api/sections", json={
        "class_id": world.class_id,
        "period": unique("Period"),
        "capacity": 10,
    }, headers=auth_header(teacher_token))
    assert resp.status_code == 201, resp.text
    section_id = resp.json()["section_id"]
    cleanup(Section, section_id)

    student_username = unique("caughtinmiddle")
    resp = client.post("/api/auth/register", json={
        "username": student_username,
        "full_name": "Caught Inmiddle",
        "password": "password123",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    student_id = resp.json()["user_id"]
    cleanup(User, student_id)
    resp = client.post("/api/auth/login", json={"username": student_username, "password": "password123"})
    assert resp.status_code == 200, resp.text
    student_token = resp.json()["access_token"]

    resp = client.post(
        f"/api/sections/{section_id}/enrollment-requests",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["enrollment_request_id"]
    cleanup(EnrollmentRequest, request_id)
    resp = client.patch(
        f"/api/enrollment-requests/{request_id}",
        json={"status": "accepted"},
        headers=auth_header(teacher_token),
    )
    assert resp.status_code == 200, resp.text

    db = SessionLocal()
    enrollment = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.student_id == student_id,
    ).first()
    db.close()
    cleanup(Enrollment, enrollment.enrollment_id)

    resp = client.delete(f"/api/users/{teacher_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/sections/{section_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "pending_reassignment"

    resp = client.get("/api/notifications", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    assert any("pending teacher reassignment" in n["message"] for n in resp.json())


def test_self_delete_teacher_cascades_sections_to_pending_reassignment(client, world, cleanup):
    teacher_username = unique("selfdroppedteacher")
    resp = client.post("/api/auth/register", json={
        "username": teacher_username,
        "full_name": "Self Dropped Teacher",
        "password": "password123",
        "school_code": world.school_code,
        "role": "teacher",
    })
    assert resp.status_code == 201, resp.text
    teacher_id = resp.json()["user_id"]
    cleanup(User, teacher_id)
    resp = client.patch(f"/api/users/{teacher_id}/verify", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    resp = client.post("/api/auth/login", json={"username": teacher_username, "password": "password123"})
    assert resp.status_code == 200, resp.text
    teacher_token = resp.json()["access_token"]

    resp = client.post("/api/sections", json={
        "class_id": world.class_id,
        "period": unique("Period"),
        "capacity": 10,
    }, headers=auth_header(teacher_token))
    assert resp.status_code == 201, resp.text
    section_id = resp.json()["section_id"]
    cleanup(Section, section_id)

    student_username = unique("selfcaughtinmiddle")
    resp = client.post("/api/auth/register", json={
        "username": student_username,
        "full_name": "Self Caught Inmiddle",
        "password": "password123",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    student_id = resp.json()["user_id"]
    cleanup(User, student_id)
    resp = client.post("/api/auth/login", json={"username": student_username, "password": "password123"})
    assert resp.status_code == 200, resp.text
    student_token = resp.json()["access_token"]

    resp = client.post(
        f"/api/sections/{section_id}/enrollment-requests",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["enrollment_request_id"]
    cleanup(EnrollmentRequest, request_id)
    resp = client.patch(
        f"/api/enrollment-requests/{request_id}",
        json={"status": "accepted"},
        headers=auth_header(teacher_token),
    )
    assert resp.status_code == 200, resp.text

    db = SessionLocal()
    enrollment = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.student_id == student_id,
    ).first()
    db.close()
    cleanup(Enrollment, enrollment.enrollment_id)

    resp = client.delete("/api/users/me", headers=auth_header(teacher_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/sections/{section_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "pending_reassignment"

    resp = client.get("/api/notifications", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text
    assert any("pending teacher reassignment" in n["message"] for n in resp.json())

    resp = client.post("/api/auth/login", json={"username": teacher_username, "password": "password123"})
    assert resp.status_code == 401, resp.text


def test_self_delete_student(client, world, cleanup):
    student_username = unique("selfdeletestudent")
    resp = client.post("/api/auth/register", json={
        "username": student_username,
        "full_name": "Self Delete Student",
        "password": "password123",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    student_id = resp.json()["user_id"]
    cleanup(User, student_id)
    resp = client.post("/api/auth/login", json={"username": student_username, "password": "password123"})
    assert resp.status_code == 200, resp.text
    student_token = resp.json()["access_token"]

    resp = client.delete("/api/users/me", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text

    db = SessionLocal()
    deleted = db.query(User).filter(User.user_id == student_id).first()
    db.close()
    assert deleted.is_archived is True
    assert deleted.deleted_at is not None

    resp = client.post("/api/auth/login", json={"username": student_username, "password": "password123"})
    assert resp.status_code == 401, resp.text


def test_self_delete_last_admin_blocked(client, world):
    # world.admin is the sole admin in its school -- self-delete must be
    # refused, and refusal must leave the account fully untouched.
    resp = client.delete("/api/users/me", headers=auth_header(world.admin_token))
    assert resp.status_code == 409, resp.text

    # get_user filters is_archived == False, so a 200 here already proves
    # the blocked self-delete left the account fully untouched.
    resp = client.get(f"/api/users/{world.admin_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["user_id"] == world.admin_id


def test_self_delete_non_last_admin_allowed(client, world, cleanup):
    second_admin_username = unique("secondadmin")
    resp = client.post("/api/auth/register", json={
        "username": second_admin_username,
        "full_name": "Second Admin",
        "password": "password123",
        "school_code": world.school_code,
        "role": "admin",
    })
    assert resp.status_code == 201, resp.text
    second_admin_id = resp.json()["user_id"]
    cleanup(User, second_admin_id)

    resp = client.patch(
        f"/api/users/{second_admin_id}/verify",
        json={"confirm_role": "admin"},
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = client.post("/api/auth/login", json={
        "username": second_admin_username,
        "password": "password123",
    })
    assert resp.status_code == 200, resp.text
    second_admin_token = resp.json()["access_token"]

    resp = client.delete("/api/users/me", headers=auth_header(second_admin_token))
    assert resp.status_code == 200, resp.text

    # world.admin is untouched and still the sole active admin afterward.
    resp = client.get(f"/api/users/{world.admin_id}", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text


def test_student_request_password_reset_notifies_admins(client, world, cleanup):
    student_username = unique("resetrequester")
    resp = client.post("/api/auth/register", json={
        "username": student_username,
        "full_name": "Reset Requester",
        "password": "password123",
        "school_code": world.school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    student_id = resp.json()["user_id"]
    cleanup(User, student_id)
    resp = client.post("/api/auth/login", json={"username": student_username, "password": "password123"})
    assert resp.status_code == 200, resp.text
    student_token = resp.json()["access_token"]

    resp = client.post("/api/users/me/request-password-reset", headers=auth_header(student_token))
    assert resp.status_code == 200, resp.text

    # Round-trips the new enum value through the API end to end -- this is
    # exactly what would 500 if the enum were only added to one of the two
    # hand-duplicated NotificationTypeEnum definitions.
    resp = client.get("/api/notifications", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    matches = [
        n for n in resp.json()
        if n["type"] == "password_reset_requested" and student_username in n["message"]
    ]
    assert matches, resp.json()
    cleanup(Notification, matches[0]["notification_id"])


def test_request_password_reset_forbidden_for_teacher_and_admin(client, world):
    resp = client.post("/api/users/me/request-password-reset", headers=auth_header(world.teacher_token))
    assert resp.status_code == 403

    resp = client.post("/api/users/me/request-password-reset", headers=auth_header(world.admin_token))
    assert resp.status_code == 403


def test_get_student_grades_across_sections(client, world, cleanup):
    from models.assignment_model import Assignment
    from models.submission_model import Submission

    resp = client.post(
        f"/api/sections/{world.section_id}/assignments",
        json={
            "title": unique("HW"),
            "due_date": "2027-01-01T00:00:00Z",
            "point_value": 100,
            "category": "homework",
        },
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 201, resp.text
    assignment_id = resp.json()["assignment_id"]
    cleanup(Assignment, assignment_id)

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
        json={"grade": 85},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/api/submissions/{submission_id}/finalize", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/users/{world.student_id}/grades", headers=auth_header(world.admin_token))
    assert resp.status_code == 200, resp.text
    grades = resp.json()
    section_grade = next(g for g in grades if g["section_id"] == world.section_id)
    assert section_grade["percentage"] == 85.0
    assert section_grade["letter_grade"] == "B"


def test_get_student_grades_forbidden_for_non_admin(client, world):
    resp = client.get(f"/api/users/{world.student_id}/grades", headers=auth_header(world.teacher_token))
    assert resp.status_code == 403


def test_get_student_grades_rejects_non_student(client, world):
    resp = client.get(f"/api/users/{world.teacher_id}/grades", headers=auth_header(world.admin_token))
    assert resp.status_code == 400
