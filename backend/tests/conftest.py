# tests/conftest.py
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from main import app
from db.pool import SessionLocal
from auth_utils import RefreshToken
from models.school_model import School
from models.user_model import User
from models.section_model import Section
from models.enrollment_model import Enrollment, EnrollmentRequest
from models.notification_model import Notification
from models.submission_model import Submission
from models.quest_completion_model import QuestCompletion
from models.point_transaction_model import PointTransaction
from models.help_request_model import HelpRequestAcceptance
from models.study_room_model import RoomMember
from models.class_request_model import ClassRequest


def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# The app's lifespan starts/stops a module-level APScheduler singleton
# (see main.py), which raises if started or shut down twice. So only one
# TestClient context for `app` may ever be open at a time -- every fixture
# below shares this single session-scoped client instead of opening its own.
@pytest.fixture(scope="session")
def _app_client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(_app_client):
    return _app_client


@pytest.fixture(scope="module")
def mod_client(_app_client):
    return _app_client


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def mod_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# Tables with a non-cascading FK to users.user_id that are pure leaves (no
# other table references their own PK), populated as unavoidable side
# effects of exercising the API (login always writes a RefreshToken; most
# teacher/admin actions notify students, etc). Swept automatically whenever
# a User row is torn down so individual tests don't need to know the ids of
# rows they never got back from a response body.
_USER_DEPENDENT_LEAF_TABLES = [
    (RefreshToken, "user_id"),
    (Notification, "user_id"),
    (Submission, "student_id"),
    (QuestCompletion, "student_id"),
    (PointTransaction, "user_id"),
    (HelpRequestAcceptance, "user_id"),
    (RoomMember, "user_id"),
    (ClassRequest, "requested_by"),
]


def _delete_row(session, model, pk_value=None, filters=None):
    if model is User:
        for dep_model, fk_col in _USER_DEPENDENT_LEAF_TABLES:
            session.query(dep_model).filter(getattr(dep_model, fk_col) == pk_value).delete(synchronize_session=False)
        session.commit()
    if filters:
        session.query(model).filter_by(**filters).delete(synchronize_session=False)
    else:
        pk_col = inspect(model).primary_key[0]
        session.query(model).filter(pk_col == pk_value).delete(synchronize_session=False)
    session.commit()


@pytest.fixture
def cleanup(db):
    """LIFO registry of rows created during a test.

    Register right after creating each row, in creation order. Teardown pops
    in reverse so children are deleted before the parents they reference,
    which matters because most FKs in this schema have no ON DELETE rule.

    For single-column-PK models: cleanup(Model, pk_value).
    For composite-PK models (HelpRequestAcceptance, RoomMember): cleanup(Model, help_request_id=1, user_id=2).
    """
    created = []

    def register(model, pk_value=None, **filters):
        created.append((model, pk_value, filters))
        return pk_value

    yield register

    for model, pk_value, filters in reversed(created):
        _delete_row(db, model, pk_value, filters)


@pytest.fixture(scope="module")
def world(mod_client, mod_db):
    """Builds School -> admin/teacher/student -> Section -> accepted Enrollment.

    Shared once per test module so every test in a file doesn't have to pay
    for a fresh school+users+section round trip. Individual tests must not
    mutate/delete these shared rows directly (e.g. don't delete world.section_id
    or world.teacher_id) -- create their own throwaway resources instead.
    """
    created = []

    def register(model, pk_value):
        created.append((model, pk_value))
        return pk_value

    school_name = unique("School")
    admin_username = unique("admin")
    resp = mod_client.post("/api/schools", json={
        "school_name": school_name,
        "admin_username": admin_username,
        "admin_password": "password123",
    })
    assert resp.status_code == 201, resp.text
    school_data = resp.json()
    school_id = school_data["school_id"]
    school_code = school_data["school_code"]
    admin_token = school_data["access_token"]
    admin_id = school_data["admin_user_id"]
    register(School, school_id)
    register(User, admin_id)

    teacher_username = unique("teacher")
    resp = mod_client.post("/api/auth/register", json={
        "username": teacher_username,
        "password": "password123",
        "school_code": school_code,
        "role": "teacher",
    })
    assert resp.status_code == 201, resp.text
    teacher_id = resp.json()["user_id"]
    register(User, teacher_id)

    resp = mod_client.patch(f"/api/users/{teacher_id}/verify", headers=auth_header(admin_token))
    assert resp.status_code == 200, resp.text

    resp = mod_client.post("/api/auth/login", json={
        "username": teacher_username,
        "password": "password123",
    })
    assert resp.status_code == 200, resp.text
    teacher_token = resp.json()["access_token"]

    student_username = unique("student")
    resp = mod_client.post("/api/auth/register", json={
        "username": student_username,
        "password": "password123",
        "school_code": school_code,
        "role": "student",
    })
    assert resp.status_code == 201, resp.text
    student_id = resp.json()["user_id"]
    register(User, student_id)

    resp = mod_client.post("/api/auth/login", json={
        "username": student_username,
        "password": "password123",
    })
    assert resp.status_code == 200, resp.text
    student_token = resp.json()["access_token"]

    resp = mod_client.get("/api/classes", headers=auth_header(teacher_token))
    assert resp.status_code == 200, resp.text
    classes = resp.json()
    assert classes, "expected seeded classes to exist"
    class_id = classes[0]["class_id"]

    resp = mod_client.post("/api/sections", json={
        "class_id": class_id,
        "period": unique("Period"),
        "capacity": 30,
    }, headers=auth_header(teacher_token))
    assert resp.status_code == 201, resp.text
    section_id = resp.json()["section_id"]
    register(Section, section_id)

    resp = mod_client.post(
        f"/api/sections/{section_id}/enrollment-requests",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 201, resp.text
    enrollment_request_id = resp.json()["enrollment_request_id"]
    register(EnrollmentRequest, enrollment_request_id)

    resp = mod_client.patch(
        f"/api/enrollment-requests/{enrollment_request_id}",
        json={"status": "accepted"},
        headers=auth_header(teacher_token),
    )
    assert resp.status_code == 200, resp.text

    enrollment = mod_db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.student_id == student_id,
    ).first()
    assert enrollment is not None
    register(Enrollment, enrollment.enrollment_id)

    yield SimpleNamespace(
        school_id=school_id,
        school_code=school_code,
        admin_token=admin_token,
        admin_id=admin_id,
        teacher_token=teacher_token,
        teacher_id=teacher_id,
        teacher_username=teacher_username,
        student_token=student_token,
        student_id=student_id,
        student_username=student_username,
        class_id=class_id,
        section_id=section_id,
        enrollment_request_id=enrollment_request_id,
        enrollment_id=enrollment.enrollment_id,
    )

    for model, pk_value in reversed(created):
        _delete_row(mod_db, model, pk_value)
