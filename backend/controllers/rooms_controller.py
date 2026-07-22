import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

import daily_client
from auth_utils import decode_token
from ws_auth import ws_token_from_subprotocol
from db.data_events import emit_data_event, resolve_section_audience
from db.pool import get_db, SessionLocal
from db.ws_broadcast import notify_room_message
from dependencies import get_current_user
from models.help_request_model import HelpRequestStatusEnum
from models.study_room_model import StudyRoom, RoomMember, StudyRoomStatusEnum
from models.user_model import User, RoleEnum
from schemas.study_room import StudyRoomResponse, StudyRoomExtendResponse, VideoTokenResponse

router = APIRouter(prefix="/rooms", tags=["rooms"])
logger = logging.getLogger(__name__)

# In-memory registry — never persisted to DB
# Structure: { room_id: { user_id: WebSocket } }
room_registry: dict = {}

# In-memory chat history for the room's lifetime — cleared as soon as the room closes.
# Structure: { room_id: [ {user_id, username, content, sent_at}, ... ] }
room_messages: dict = {}


class KickRequest(BaseModel):
    user_id: int


def _get_room_or_404(room_id: int, db: Session) -> StudyRoom:
    room = db.query(StudyRoom).filter(StudyRoom.room_id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found.")
    return room


def _require_requester(room: StudyRoom, user_id: int):
    if room.help_request.requester_id != user_id:
        raise HTTPException(status_code=403, detail="Only the room requester can perform this action.")


def _emit_room_events(db: Session, room: StudyRoom, room_action: str, hr_action: Optional[str] = None):
    """Queue rooms (and optionally help_requests) data events for everyone in
    the room's section. Delivered on the caller's next db.commit()."""
    section = room.help_request.section
    audience = resolve_section_audience(db, section)
    emit_data_event(
        db, "rooms", room_action, section.school_id, audience,
        section_id=section.section_id, ids={"room_id": room.room_id},
    )
    if hr_action is not None:
        emit_data_event(
            db, "help_requests", hr_action, section.school_id, audience,
            section_id=section.section_id,
            ids={"help_request_id": room.help_request_id, "room_id": room.room_id},
        )


def _build_room_response(room: StudyRoom) -> dict:
    return {
        "room_id": room.room_id,
        "help_request_id": room.help_request_id,
        "requester_id": room.help_request.requester_id,
        "members": [
            {"user_id": m.user_id, "username": m.user.username}
            for m in room.members
        ],
        "timer_ends_at": room.timer_ends_at,
        "status": room.status,
        "daily_room_url": room.daily_room_url,
    }


def _teardown_daily_room(room: StudyRoom):
    """Best-effort Daily room deletion — called everywhere a study room
    closes or is deleted. Never raises: the room's own close/delete has
    already committed by the time this runs, so a Daily-side failure here
    just means that room lingers until its own exp cleans it up."""
    if not room.daily_room_name:
        return
    try:
        daily_client.delete_room(room.daily_room_name)
    except Exception:
        logger.exception("Failed to delete Daily room for study room %s", room.room_id)


async def _close_room_connections(
    room_id: int,
    requester_id: Optional[int] = None,
    notify_type: Optional[str] = None,
):
    """Disconnect all WS connections for a room. If requester_id is given, that
    connection first gets a session-confirmation prompt. If notify_type is given,
    every connection first gets a {"type": notify_type} message (e.g. room deletion)."""
    room_messages.pop(room_id, None)

    if room_id not in room_registry:
        return

    if notify_type:
        for ws in list(room_registry[room_id].values()):
            try:
                await ws.send_json({"type": notify_type})
            except Exception:
                pass
    elif requester_id and requester_id in room_registry[room_id]:
        try:
            await room_registry[room_id][requester_id].send_json({
                "type": "session_confirmation_required",
            })
        except Exception:
            pass

    connections = list(room_registry.pop(room_id, {}).values())
    for ws in connections:
        try:
            await ws.close(code=1000)
        except Exception:
            pass


@router.get("/{room_id}", response_model=StudyRoomResponse)
def get_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room_or_404(room_id, db)

    if current_user.role == RoleEnum.student:
        member = db.query(RoomMember).filter(
            RoomMember.room_id == room_id,
            RoomMember.user_id == current_user.user_id,
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not a room member.")
    else:
        section = room.help_request.section
        if section.school_id != current_user.school_id:
            raise HTTPException(status_code=403, detail="Access denied.")

    return _build_room_response(room)


@router.post("/{room_id}/video-token", response_model=VideoTokenResponse)
def get_video_token(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room_or_404(room_id, db)

    member = db.query(RoomMember).filter(
        RoomMember.room_id == room_id,
        RoomMember.user_id == current_user.user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a room member.")
    if room.status != StudyRoomStatusEnum.active:
        raise HTTPException(status_code=409, detail="Room is not active.")
    if not room.daily_room_name:
        raise HTTPException(status_code=503, detail="Video chat is not available for this room.")

    is_owner = current_user.user_id == room.help_request.requester_id
    try:
        token = daily_client.create_meeting_token(
            room.daily_room_name,
            current_user.username,
            is_owner,
            int(room.timer_ends_at.timestamp()),
        )
    except Exception:
        logger.exception("Failed to create Daily meeting token for study room %s", room.room_id)
        raise HTTPException(status_code=503, detail="Video chat is temporarily unavailable.")

    return VideoTokenResponse(token=token, room_url=room.daily_room_url)


@router.post("/{room_id}/kick")
async def kick_member(
    room_id: int,
    body: KickRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room_or_404(room_id, db)
    _require_requester(room, current_user.user_id)

    if body.user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot kick yourself.")

    member = db.query(RoomMember).filter(
        RoomMember.room_id == room_id,
        RoomMember.user_id == body.user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="User not in this room.")

    db.delete(member)
    db.commit()

    # Disconnect kicked user's WS if connected
    if room_id in room_registry and body.user_id in room_registry[room_id]:
        try:
            await room_registry[room_id][body.user_id].close(code=1000)
        except Exception:
            pass
        del room_registry[room_id][body.user_id]

    # Check if only the requester remains in DB members
    remaining = db.query(RoomMember).filter(RoomMember.room_id == room_id).count()
    if remaining <= 1:
        room.status = StudyRoomStatusEnum.closed
        db.commit()
        _teardown_daily_room(room)
        await _close_room_connections(room_id, requester_id=current_user.user_id)

    _emit_room_events(db, room, "updated", hr_action="updated")
    db.commit()
    return {"message": "Member removed from room."}


@router.post("/{room_id}/leave")
async def leave_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room_or_404(room_id, db)

    member = db.query(RoomMember).filter(
        RoomMember.room_id == room_id,
        RoomMember.user_id == current_user.user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a room member.")

    db.delete(member)
    db.commit()

    # Disconnect the leaving user's own WS if connected
    if room_id in room_registry and current_user.user_id in room_registry[room_id]:
        try:
            await room_registry[room_id][current_user.user_id].close(code=1000)
        except Exception:
            pass
        del room_registry[room_id][current_user.user_id]

    # Only tear the room down once it's truly empty — a solo requester's room
    # stays active so a departed/kicked member (or a new student) can still
    # join back in, per the help-request reopen logic just below.
    remaining = db.query(RoomMember).filter(RoomMember.room_id == room_id).count()
    if remaining == 0 and room.status == StudyRoomStatusEnum.active:
        room.status = StudyRoomStatusEnum.closed
        db.commit()
        _teardown_daily_room(room)
        await _close_room_connections(room_id, requester_id=room.help_request.requester_id)

    # Keep the help request's participant count in sync with who's actually left in the room,
    # reopen it if it's no longer full, and close it out once nobody remains.
    help_request = room.help_request
    help_request.current_size = remaining
    if remaining == 0:
        help_request.status = HelpRequestStatusEnum.closed
        help_request.is_archived = True
    elif remaining < help_request.group_size and help_request.status == HelpRequestStatusEnum.active:
        help_request.status = HelpRequestStatusEnum.open
    _emit_room_events(db, room, "updated", hr_action="updated")
    db.commit()

    return {"message": "Left the room."}


@router.post("/{room_id}/extend", response_model=StudyRoomExtendResponse)
def extend_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room_or_404(room_id, db)
    _require_requester(room, current_user.user_id)

    if room.status != StudyRoomStatusEnum.active:
        raise HTTPException(status_code=409, detail="Room is not active.")

    room.timer_ends_at = room.timer_ends_at + timedelta(minutes=10)
    _emit_room_events(db, room, "updated")
    db.commit()
    db.refresh(room)

    notify_room_message(
        db,
        room_id,
        {"type": "timer_extended", "timer_ends_at": room.timer_ends_at.isoformat()},
        sender_id=current_user.user_id,
    )

    return room


@router.post("/{room_id}/close")
async def close_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room_or_404(room_id, db)
    _require_requester(room, current_user.user_id)

    if room.status == StudyRoomStatusEnum.closed:
        raise HTTPException(status_code=409, detail="Room is already closed.")

    room.status = StudyRoomStatusEnum.closed

    # Closing the room is terminal for its help request too — without this,
    # the help request was left dangling at its prior status (active/open)
    # forever, showing on the bulletin board with no room to back it.
    help_request = room.help_request
    help_request.status = HelpRequestStatusEnum.closed
    help_request.is_archived = True

    _emit_room_events(db, room, "updated", hr_action="deleted")
    db.commit()

    _teardown_daily_room(room)
    await _close_room_connections(room_id, requester_id=current_user.user_id)
    return {"message": "Room closed."}


@router.delete("/{room_id}")
async def delete_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room_or_404(room_id, db)
    _require_requester(room, current_user.user_id)

    # The requester has full autonomy to delete the room at any time, active or
    # closed — this is a hard teardown, not the graceful /close flow, so there's
    # no session-confirmation prompt: just notify everyone and disconnect them.
    _teardown_daily_room(room)
    await _close_room_connections(room_id, notify_type="room_deleted")

    # Deletion is terminal — archive the help request too so it stops
    # cluttering the bulletin board now that its room is gone for good.
    help_request = room.help_request
    help_request.status = HelpRequestStatusEnum.closed
    help_request.is_archived = True

    _emit_room_events(db, room, "deleted", hr_action="deleted")
    db.query(RoomMember).filter(RoomMember.room_id == room_id).delete()
    db.delete(room)
    db.commit()

    return {"message": "Room deleted."}


@router.websocket("/{room_id}/chat")
async def chat(websocket: WebSocket, room_id: int):
    # Validate JWT
    try:
        token = ws_token_from_subprotocol(websocket)
        payload = decode_token(token)
        user_id: int = payload["user_id"]
    except Exception:
        await websocket.close(code=4001)
        return

    # Verify room/membership with a short-lived session — not held for the
    # life of the connection, since the socket can stay open a long time.
    db = SessionLocal()
    try:
        room = db.query(StudyRoom).filter(StudyRoom.room_id == room_id).first()
        if not room or room.status != StudyRoomStatusEnum.active:
            await websocket.close(code=4003)
            return

        member = db.query(RoomMember).filter(
            RoomMember.room_id == room_id,
            RoomMember.user_id == user_id,
        ).first()
        if not member:
            await websocket.close(code=4001)
            return

        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            await websocket.close(code=4001)
            return

        username = user.username
    finally:
        db.close()

    await websocket.accept()

    # Register connection
    if room_id not in room_registry:
        room_registry[room_id] = {}
    room_registry[room_id][user_id] = websocket

    # Replay this room's history so far (cleared when the room closes) so a
    # newly connected or reconnecting member sees the full conversation.
    for past_message in room_messages.get(room_id, []):
        try:
            await websocket.send_json(past_message)
        except Exception:
            break

    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content", "")
            if not content:
                continue

            message_out = {
                "user_id": user_id,
                "username": username,
                "content": content,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
            # Not appended to room_messages directly here — every backend
            # process (including this one) receives its own NOTIFY back via
            # deliver_loop, which is the single place history gets recorded.
            # See deliver_loop's docstring for why.
            notify_room_message(db, room_id, message_out, sender_id=user_id)

    except WebSocketDisconnect:
        pass
    finally:
        # Remove this connection from the registry. A dropped websocket (page
        # navigation, refresh, tab switch, brief network blip — there's no
        # reconnect support) does NOT mean the member left the room; actual
        # departures are tracked via /leave and /kick against real DB
        # membership, not live socket presence. Auto-closing here would wipe
        # out the room (and its chat history) on a transient disconnect.
        if room_id in room_registry:
            room_registry[room_id].pop(user_id, None)
            if not room_registry.get(room_id):
                room_registry.pop(room_id, None)
