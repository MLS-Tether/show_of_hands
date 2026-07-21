import enum
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class StudyRoomStatusEnum(str, enum.Enum):
    active = "active"
    closed = "closed"


class RoomMemberBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str


class StudyRoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room_id: int
    help_request_id: int
    requester_id: int
    members: List[RoomMemberBrief]
    timer_ends_at: datetime
    status: StudyRoomStatusEnum
    daily_room_url: Optional[str] = None


class StudyRoomExtendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room_id: int
    timer_ends_at: datetime


class VideoTokenResponse(BaseModel):
    token: str
    room_url: str
