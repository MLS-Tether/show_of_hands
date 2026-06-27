import enum
from datetime import datetime
from typing import List
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
    members: List[RoomMemberBrief]
    timer_ends_at: datetime
    status: StudyRoomStatusEnum


class StudyRoomExtendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room_id: int
    timer_ends_at: datetime
