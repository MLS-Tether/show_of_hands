import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth_utils import decode_token
from ws_auth import ws_token_from_subprotocol
from db.pool import get_db, SessionLocal
from db.ws_broadcast import notification_queue, data_events_queue
from dependencies import get_current_user, require_role
from models.enrollment_model import Enrollment
from models.notification_model import Notification, NotificationTypeEnum
from models.section_model import Section
from models.user_model import User
from notifications import notify
from schemas.notification import NotificationResponse, NotificationReadResponse

router = APIRouter(tags=["notifications"])
logger = logging.getLogger(__name__)

# In-memory registry — never persisted to DB.
# Structure: { user_id: [WebSocket, ...] } — a list since a user may have
# several tabs/devices open at once.
notification_registry: dict = {}


class SectionNotifyRequest(BaseModel):
    message: str


@router.get("/notifications", response_model=List[NotificationResponse])
def list_notifications(
    is_read: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
    )
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    return query.order_by(Notification.created_at.desc()).all()


# read-all MUST be registered before /{notification_id}/read to avoid path collision
@router.patch("/notifications/read-all")
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read."}


@router.patch("/notifications/{notification_id}/read", response_model=NotificationReadResponse)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.user_id == current_user.user_id,
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/sections/{section_id}/notify")
def notify_section(
    section_id: int,
    body: SectionNotifyRequest,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    enrolled = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.is_archived == False,
    ).all()

    notify(
        db,
        [e.student_id for e in enrolled],
        NotificationTypeEnum.section_status,
        body.message,
        entity_type="section",
        entity_id=section_id,
    )

    db.commit()
    return {"message": f"Notification sent to {len(enrolled)} student(s)."}


@router.websocket("/notifications/stream")
async def notifications_stream(websocket: WebSocket):
    try:
        token = ws_token_from_subprotocol(websocket)
        payload = decode_token(token)
        user_id: int = payload["user_id"]
    except (ValueError, HTTPException):
        # Expected/benign: no token, or an expired/invalid one.
        await websocket.close(code=4001)
        return
    except Exception:
        # Anything else (e.g. a malformed payload missing "user_id") is a
        # real bug, not just a stale token — log it so it doesn't disappear
        # into the same silent close as the expected case above.
        logger.exception("Unexpected error during notifications WS auth")
        await websocket.close(code=4001)
        return

    # The client sent the auth token as a Sec-WebSocket-Protocol subprotocol
    # (see utils/ws.js) — per RFC 6455, the server must echo one back or the
    # browser treats the handshake itself as failed, even though the raw
    # upgrade otherwise succeeds.
    await websocket.accept(subprotocol=token)
    notification_registry.setdefault(user_id, []).append(websocket)

    try:
        while True:
            # The client never sends anything meaningful over this socket —
            # it exists purely for server -> client push. Just keep it open.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connections = notification_registry.get(user_id)
        if connections and websocket in connections:
            connections.remove(websocket)
        if connections is not None and not connections:
            notification_registry.pop(user_id, None)


async def deliver_notifications():
    """Runs as an asyncio task. Reads relayed {user_id, notification_id}
    payloads off the queue (fired by a Postgres trigger on every notifications
    insert) and pushes the full notification to any of that user's locally-
    connected WebSocket clients."""
    while True:
        raw_payload = await notification_queue.get()
        try:
            data = json.loads(raw_payload)
        except json.JSONDecodeError:
            continue

        user_id = data.get("user_id")
        notification_id = data.get("notification_id")
        if user_id is None or notification_id is None:
            continue

        connections = notification_registry.get(user_id)
        if not connections:
            continue

        db = SessionLocal()
        try:
            notification = db.query(Notification).filter(
                Notification.notification_id == notification_id,
            ).first()
        finally:
            db.close()
        if not notification:
            continue

        message = {
            "type": "new_notification",
            "notification": {
                "notification_id": notification.notification_id,
                "type": notification.type.value,
                "message": notification.message,
                "is_read": notification.is_read,
                "entity_type": notification.entity_type,
                "entity_id": notification.entity_id,
                "created_at": notification.created_at.isoformat(),
            },
        }

        dead_connections = []
        for ws in list(connections):
            try:
                await ws.send_json(message)
            except Exception:
                # Expected if that client already disconnected.
                logger.debug("Failed to deliver notification to user %s", user_id, exc_info=True)
                dead_connections.append(ws)
        for ws in dead_connections:
            # This same connection can already have been removed by the
            # socket's own disconnect handler while the send above was
            # in flight — an unguarded .remove() would raise ValueError and
            # kill this whole delivery loop for the rest of the process.
            if ws in connections:
                connections.remove(ws)


async def route_data_event(data: dict, registry: dict):
    """Push one data-change event to its audience's connected sockets.
    Separated from the queue loop so tests can call it directly."""
    message = {"type": "data_event", "event": data}
    if data.get("broadcast_school"):
        # A large-audience event only carries school_id, not individual
        # user_ids (see BROADCAST_AUDIENCE_THRESHOLD in db/data_events.py) —
        # resolve which connected users actually belong to that school so
        # this doesn't fan out to every tenant on the server.
        school_id = data.get("school_id")
        db = SessionLocal()
        try:
            rows = db.query(User.user_id).filter(
                User.school_id == school_id,
                User.is_archived == False,
            ).all()
        finally:
            db.close()
        school_user_ids = {r[0] for r in rows}
        target_ids = [uid for uid in registry.keys() if uid in school_user_ids]
    else:
        target_ids = data.get("user_ids") or []

    for user_id in target_ids:
        connections = registry.get(user_id)
        if not connections:
            continue
        dead_connections = []
        for ws in list(connections):
            try:
                await ws.send_json(message)
            except Exception:
                # Expected if that client already disconnected.
                logger.debug("Failed to deliver data event to user %s", user_id, exc_info=True)
                dead_connections.append(ws)
        for ws in dead_connections:
            if ws in connections:
                connections.remove(ws)


async def deliver_data_events():
    """Runs as an asyncio task. Reads relayed data-change payloads off the
    queue (fired by emit_data_event in mutating controllers) and pushes them
    to each affected user's connected notification sockets, where the
    frontend maps them to cache invalidations."""
    while True:
        raw_payload = await data_events_queue.get()
        try:
            data = json.loads(raw_payload)
        except json.JSONDecodeError:
            continue
        await route_data_event(data, notification_registry)
