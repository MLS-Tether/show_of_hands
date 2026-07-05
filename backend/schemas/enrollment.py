from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

EnrollmentRequestStatus = Literal["pending", "approved", "rejected"]


class EnrollmentRequestCreateResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    enrollment_request_id: int
    section_id: int
    student_id: int
    status: EnrollmentRequestStatus
    created_at: datetime


class EnrollmentRequestListItem(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    enrollment_request_id: int
    student_id: int
    username: str
    status: EnrollmentRequestStatus
    created_at: datetime


class EnrollmentRequestUpdate(BaseModel):

    status: Literal["approved", "rejected"]


class EnrollmentRequestUpdateResponse(BaseModel):

    enrollment_request_id: int
    status: Literal["approved", "rejected"]


class MessageResponse(BaseModel):

    message: str