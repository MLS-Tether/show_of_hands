import json
from typing import Iterable, List, Optional

from sqlalchemy import text

from db.ws_broadcast import DATA_EVENTS_CHANNEL
from models.enrollment_model import Enrollment
from models.user_model import User, RoleEnum

# pg_notify payloads are capped at ~8000 bytes; past this many recipients we
# stop listing user ids and tell the delivery loop to fan out to everyone
# connected instead.
BROADCAST_AUDIENCE_THRESHOLD = 500


def emit_data_event(
    db,
    entity: str,
    action: str,
    school_id: int,
    user_ids: Iterable[int],
    section_id: Optional[int] = None,
    ids: Optional[dict] = None,
    broadcast: bool = False,
):
    """Queue a pg_notify on the caller's session. Because NOTIFY is
    transactional, the event is only delivered when the caller's existing
    db.commit() succeeds — call this right before that commit."""
    unique_ids = sorted(set(user_ids))
    payload = {
        "entity": entity,
        "action": action,
        "school_id": school_id,
        "section_id": section_id,
        "ids": ids or {},
    }
    if broadcast or len(unique_ids) > BROADCAST_AUDIENCE_THRESHOLD:
        payload["broadcast_school"] = True
    else:
        payload["user_ids"] = unique_ids

    db.execute(
        text("SELECT pg_notify(:channel, :payload)"),
        {"channel": DATA_EVENTS_CHANNEL, "payload": json.dumps(payload)},
    )


def resolve_admin_ids(db, school_id: int) -> List[int]:
    rows = db.query(User.user_id).filter(
        User.school_id == school_id,
        User.role == RoleEnum.admin,
        User.is_archived == False,
    ).all()
    return [r[0] for r in rows]


def resolve_section_audience(db, section) -> List[int]:
    """Everyone whose cached data a section-scoped change can invalidate:
    non-archived enrolled students, the section's teacher, and school admins."""
    rows = db.query(Enrollment.student_id).filter(
        Enrollment.section_id == section.section_id,
        Enrollment.is_archived == False,
    ).all()
    audience = [r[0] for r in rows]
    if section.teacher_id is not None:
        audience.append(section.teacher_id)
    audience.extend(resolve_admin_ids(db, section.school_id))
    return audience


def resolve_admin_audience(db, school_id: int, extra_user_ids: Iterable[int] = ()) -> List[int]:
    audience = resolve_admin_ids(db, school_id)
    audience.extend(extra_user_ids)
    return audience
