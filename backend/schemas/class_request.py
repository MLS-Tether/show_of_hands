import enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ClassRequestStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ClassRequestCreate(BaseModel):
    class_name: str
    subject: Optional[str] = None
    description: Optional[str] = None


class ClassRequestUpdateStatus(BaseModel):
    status: ClassRequestStatusEnum


class ClassRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    class_request_id: int
    class_name: str
    subject: Optional[str] = None
    description: Optional[str] = None
    status: ClassRequestStatusEnum
    created_at: datetime


class ClassRequestListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    class_request_id: int
    class_name: str
    subject: Optional[str] = None
    description: Optional[str] = None
    requested_by: int
    status: ClassRequestStatusEnum
    created_at: datetime
    similar_classes: list[str] = []


class ClassRequestStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    class_request_id: int
    status: ClassRequestStatusEnum
