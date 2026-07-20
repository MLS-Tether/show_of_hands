import asyncio
import json
import select
import time

import psycopg2
import pytest

from tests.conftest import auth_header, unique
from controllers.notifications_controller import route_data_event
from db.data_events import resolve_section_audience
from db.pool import DATABASE_URL
from models.enrollment_model import Enrollment
from models.quest_model import Quest
from models.section_model import Section
from models.user_model import User


@pytest.fixture
def listen_data_events():
    """Raw LISTEN connection on the data_events channel. Yields a helper that
    waits for the first NOTIFY payload matching a predicate — lets tests
    assert on events for rows they just created even though the dev DB is
    shared with other developers."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("LISTEN data_events;")

    def wait_for_event(predicate, timeout=10.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if select.select([conn], [], [], 0.5) != ([], [], []):
                conn.poll()
            while conn.notifies:
                notify = conn.notifies.pop(0)
                payload = json.loads(notify.payload)
                if predicate(payload):
                    return payload
        return None

    yield wait_for_event

    cur.close()
    conn.close()


def test_create_quest_emits_data_event_to_section_audience(world, client, db, cleanup, listen_data_events):
    resp = client.post(f"/api/sections/{world.section_id}/quests", json={
        "title": unique("Quest"),
        "description": "desc",
        "category": "academic",
        "point_value": 10,
        "quest_type": "daily",
        "assigned_to": "all",
    }, headers=auth_header(world.teacher_token))
    assert resp.status_code == 201, resp.text
    quest_id = resp.json()["quest_id"]
    cleanup(Quest, quest_id)

    event = listen_data_events(
        lambda p: p.get("entity") == "quests" and p.get("ids", {}).get("quest_id") == quest_id
    )
    assert event is not None, "expected a data_events NOTIFY for the created quest"
    assert event["action"] == "created"
    assert event["section_id"] == world.section_id
    assert event["school_id"] == world.school_id
    for uid in (world.student_id, world.teacher_id, world.admin_id):
        assert uid in event["user_ids"]


def test_delete_quest_emits_deleted_event(world, client, db, cleanup, listen_data_events):
    resp = client.post(f"/api/sections/{world.section_id}/quests", json={
        "title": unique("Quest"),
        "description": "desc",
        "category": "academic",
        "point_value": 10,
        "quest_type": "daily",
        "assigned_to": "all",
    }, headers=auth_header(world.teacher_token))
    assert resp.status_code == 201, resp.text
    quest_id = resp.json()["quest_id"]
    cleanup(Quest, quest_id)

    resp = client.delete(f"/api/quests/{quest_id}", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200, resp.text

    event = listen_data_events(
        lambda p: p.get("entity") == "quests"
        and p.get("action") == "deleted"
        and p.get("ids", {}).get("quest_id") == quest_id
    )
    assert event is not None, "expected a data_events NOTIFY for the deleted quest"
    assert event["section_id"] == world.section_id


def test_resolve_section_audience_excludes_archived_enrollments(world, db, cleanup):
    section = db.query(Section).filter(Section.section_id == world.section_id).first()

    archived_student = User(
        school_id=world.school_id,
        username=unique("archived_student"),
        full_name="Archived Student",
        password_hash="x",
        role="student",
        is_verified=True,
    )
    db.add(archived_student)
    db.flush()
    cleanup(User, archived_student.user_id)
    enrollment = Enrollment(
        section_id=world.section_id,
        student_id=archived_student.user_id,
        is_archived=True,
    )
    db.add(enrollment)
    db.commit()
    cleanup(Enrollment, enrollment.enrollment_id)

    audience = resolve_section_audience(db, section)
    assert world.student_id in audience
    assert world.teacher_id in audience
    assert world.admin_id in audience
    assert archived_student.user_id not in audience


class FakeWebSocket:
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []

    async def send_json(self, message):
        if self.fail:
            raise RuntimeError("dead socket")
        self.sent.append(message)


def test_route_data_event_targets_audience_only():
    ws_target = FakeWebSocket()
    ws_other = FakeWebSocket()
    registry = {1: [ws_target], 2: [ws_other]}
    event = {"entity": "quests", "action": "created", "user_ids": [1]}

    asyncio.run(route_data_event(event, registry))

    assert ws_target.sent == [{"type": "data_event", "event": event}]
    assert ws_other.sent == []


def test_route_data_event_prunes_dead_sockets():
    ws_dead = FakeWebSocket(fail=True)
    ws_live = FakeWebSocket()
    registry = {1: [ws_dead, ws_live]}
    event = {"entity": "points", "action": "updated", "user_ids": [1]}

    asyncio.run(route_data_event(event, registry))

    assert ws_live.sent and ws_live.sent[0]["type"] == "data_event"
    assert ws_dead not in registry[1]
    assert ws_live in registry[1]


def test_route_data_event_broadcast_school_reaches_all_connections():
    ws_a = FakeWebSocket()
    ws_b = FakeWebSocket()
    registry = {1: [ws_a], 2: [ws_b]}
    event = {"entity": "school", "action": "updated", "broadcast_school": True}

    asyncio.run(route_data_event(event, registry))

    assert ws_a.sent and ws_b.sent
