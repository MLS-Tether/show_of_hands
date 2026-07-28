import enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class UnenrollRequestStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class UnenrollRequestCreate(BaseModel):
    student_id: int
    reason: str


class UnenrollRequestUpdateStatus(BaseModel):
    status: UnenrollRequestStatusEnum


class UnenrollRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unenroll_request_id: int
    section_id: int
    student_id: int
    requested_by: int
    reason: str
    status: UnenrollRequestStatusEnum
    created_at: datetime


class UnenrollRequestListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unenroll_request_id: int
    section_id: int
    student_id: int
    student_username: str
    requested_by: int
    requester_username: str
    reason: str
    status: UnenrollRequestStatusEnum
    created_at: datetime


class UnenrollRequestStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unenroll_request_id: int
    status: UnenrollRequestStatusEnum


class MessageResponse(BaseModel):
    message: str
