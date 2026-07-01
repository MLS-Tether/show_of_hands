import enum
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict


class EnrollmentStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class EnrollmentStatusUpdate(BaseModel):
    status: Literal["approved", "rejected"]


class EnrollmentRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enrollment_id: int
    section_id: int
    student_id: int
    status: EnrollmentStatusEnum
    created_at: datetime


class EnrollmentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enrollment_id: int
    student_id: int
    username: str
    status: EnrollmentStatusEnum
    created_at: datetime
