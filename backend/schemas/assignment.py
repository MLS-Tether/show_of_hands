from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from models.assignment_model import AssignmentCategoryEnum


class AssignmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    due_date: datetime
    point_value: int
    category: AssignmentCategoryEnum = AssignmentCategoryEnum.homework


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    due_date: Optional[datetime] = None
    point_value: Optional[int] = None
    category: Optional[AssignmentCategoryEnum] = None


class AssignmentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    title: str
    due_date: datetime
    point_value: int
    category: AssignmentCategoryEnum


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    section_id: int
    title: str
    description: Optional[str]
    url: Optional[str] = None
    due_date: datetime
    point_value: int
    category: AssignmentCategoryEnum
    created_at: datetime


class AssignmentUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    title: str
    due_date: datetime
    point_value: int
    category: AssignmentCategoryEnum
    updated_at: datetime
