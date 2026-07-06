import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EnrollmentStatusEnum(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    archived = "archived"


class EnrollmentRequestCreateResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    enrollment_request_id: int
    section_id: int
    student_id: int
    status: EnrollmentStatusEnum
    created_at: datetime


class EnrollmentRequestListItem(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    enrollment_request_id: int
    student_id: int
    username: str
    status: EnrollmentStatusEnum
    created_at: datetime


class EnrollmentRequestUpdate(BaseModel):

    status: EnrollmentStatusEnum


class EnrollmentRequestUpdateResponse(BaseModel):

    enrollment_request_id: int
    status: EnrollmentStatusEnum


class MessageResponse(BaseModel):

    message: str