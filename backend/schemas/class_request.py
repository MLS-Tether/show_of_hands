import enum
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ClassRequestStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ClassRequestCreate(BaseModel):
    class_name: str


class ClassRequestUpdateStatus(BaseModel):
    status: ClassRequestStatusEnum


class ClassRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    class_request_id: int
    class_name: str
    status: ClassRequestStatusEnum
    created_at: datetime


class ClassRequestListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    class_request_id: int
    class_name: str
    requested_by: int
    status: ClassRequestStatusEnum
    created_at: datetime


class ClassRequestStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    class_request_id: int
    status: ClassRequestStatusEnum
