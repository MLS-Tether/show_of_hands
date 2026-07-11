import enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class HelpRequestStatusEnum(str, enum.Enum):
    open = "open"
    active = "active"
    closed = "closed"
    expired = "expired"


class HelpRequestCreate(BaseModel):
    topic: str
    description: Optional[str] = None
    group_size: int
    duration_minutes: int


class HelpRequestUpdate(BaseModel):
    topic: Optional[str] = None
    description: Optional[str] = None
    group_size: Optional[int] = None
    duration_minutes: Optional[int] = None


class HelpRequestConfirmCreate(BaseModel):
    session_occurred: bool


class AcceptedByEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    accepted_at: datetime


class HelpRequestStudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    help_request_id: int
    topic: str
    description: Optional[str]
    group_size: int
    current_size: int
    duration_minutes: int
    status: HelpRequestStatusEnum
    room_id: Optional[int] = None
    created_at: datetime


class HelpRequestTeacherResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    help_request_id: int
    requester_id: int
    requester_username: str
    topic: str
    description: Optional[str]
    group_size: int
    current_size: int
    duration_minutes: int
    status: HelpRequestStatusEnum
    accepted_by: List[AcceptedByEntry]
    room_id: Optional[int] = None
    created_at: datetime


class HelpRequestAcceptResponse(BaseModel):
    help_request_id: int
    status: HelpRequestStatusEnum
    room_id: int


class HelpRequestConfirmResponse(BaseModel):
    help_request_id: int
    session_occurred: bool
    points_awarded: int
