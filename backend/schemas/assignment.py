from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AssignmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: datetime
    point_value: int


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    point_value: Optional[int] = None


class AssignmentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    title: str
    due_date: datetime
    point_value: int


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    section_id: int
    title: str
    description: Optional[str]
    due_date: datetime
    point_value: int
    created_at: datetime


class AssignmentUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    title: str
    due_date: datetime
    point_value: int
    updated_at: datetime
