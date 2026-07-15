import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth_utils import decode_token
from db.pool import get_db, SessionLocal
from db.ws_broadcast import notification_queue
from dependencies import get_current_user, require_role
from models.enrollment_model import Enrollment
from models.notification_model import Notification, NotificationTypeEnum
from models.section_model import Section
from models.user_model import User
from schemas.notification import NotificationResponse, NotificationReadResponse

router = APIRouter(tags=["notifications"])

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

    for e in enrolled:
        db.add(Notification(
            user_id=e.student_id,
            type=NotificationTypeEnum.section_status,
            message=body.message,
        ))

    db.commit()
    return {"message": f"Notification sent to {len(enrolled)} student(s)."}


@router.websocket("/notifications/stream")
async def notifications_stream(websocket: WebSocket, token: str):
    try:
        payload = decode_token(token)
        user_id: int = payload["user_id"]
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()
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
                "created_at": notification.created_at.isoformat(),
            },
        }

        dead_connections = []
        for ws in list(connections):
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append(ws)
        for ws in dead_connections:
            connections.remove(ws)
