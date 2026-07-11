from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth_utils import decode_token
from db.pool import get_db, SessionLocal
from dependencies import get_current_user
from models.help_request_model import HelpRequestStatusEnum
from models.study_room_model import StudyRoom, RoomMember, StudyRoomStatusEnum
from models.user_model import User, RoleEnum
from schemas.study_room import StudyRoomResponse, StudyRoomExtendResponse

router = APIRouter(prefix="/rooms", tags=["rooms"])

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
    }


async def _close_room_connections(room_id: int, requester_id: Optional[int] = None):
    """Send session confirmation prompt to requester, then disconnect all WS connections."""
    room_messages.pop(room_id, None)

    if room_id not in room_registry:
        return

    if requester_id and requester_id in room_registry[room_id]:
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
        await _close_room_connections(room_id, requester_id=current_user.user_id)

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

    # If only one member (or none) remains, close the room like a kick would
    remaining = db.query(RoomMember).filter(RoomMember.room_id == room_id).count()
    if remaining <= 1 and room.status == StudyRoomStatusEnum.active:
        room.status = StudyRoomStatusEnum.closed
        db.commit()
        await _close_room_connections(room_id, requester_id=room.help_request.requester_id)

    # Keep the help request's participant count in sync with who's actually left in the room,
    # reopen it if it's no longer full, and close it out once nobody remains.
    help_request = room.help_request
    help_request.current_size = remaining
    if remaining == 0:
        help_request.status = HelpRequestStatusEnum.closed
    elif remaining < help_request.group_size and help_request.status == HelpRequestStatusEnum.active:
        help_request.status = HelpRequestStatusEnum.open
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
    db.commit()
    db.refresh(room)
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
    db.commit()

    await _close_room_connections(room_id, requester_id=current_user.user_id)
    return {"message": "Room closed."}


@router.delete("/{room_id}")
def delete_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room_or_404(room_id, db)
    _require_requester(room, current_user.user_id)

    if room.status != StudyRoomStatusEnum.closed:
        raise HTTPException(status_code=409, detail="Only a closed room can be deleted.")

    db.query(RoomMember).filter(RoomMember.room_id == room_id).delete()
    db.delete(room)
    db.commit()

    return {"message": "Room deleted."}


@router.websocket("/{room_id}/chat")
async def chat(websocket: WebSocket, room_id: int, token: str, db: Session = Depends(get_db)):
    # Validate JWT
    try:
        payload = decode_token(token)
        user_id: int = payload["user_id"]
    except Exception:
        await websocket.close(code=4001)
        return

    # Verify room exists and is active
    room = db.query(StudyRoom).filter(StudyRoom.room_id == room_id).first()
    if not room or room.status != StudyRoomStatusEnum.active:
        await websocket.close(code=4003)
        return

    # Verify user is a room member
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
                "username": user.username,
                "content": content,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
            room_messages.setdefault(room_id, []).append(message_out)

            # Broadcast to all other connections in this room
            dead_connections = []
            for other_user_id, other_ws in list(room_registry.get(room_id, {}).items()):
                if other_user_id != user_id:
                    try:
                        await other_ws.send_json(message_out)
                    except Exception:
                        dead_connections.append(other_user_id)

            for dead_id in dead_connections:
                room_registry.get(room_id, {}).pop(dead_id, None)

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
