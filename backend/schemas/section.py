import enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class SectionStatusEnum(str, enum.Enum):
    active = "active"
    archived = "archived"
    pending_reassignment = "pending_reassignment"


# Inline brief schemas used in SectionDetailResponse
class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str


class AssignmentBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    title: str
    due_date: datetime


class QuestBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quest_id: int
    title: str
    category: str


class SectionCreate(BaseModel):
    class_id: int
    period: str
    capacity: int


class SectionUpdate(BaseModel):
    period: Optional[str] = None
    capacity: Optional[int] = None
    status: Optional[SectionStatusEnum] = None
    teacher_id: Optional[int] = None


class SectionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    section_id: int
    class_name: str
    teacher_name: Optional[str]
    period: str
    enrolled_count: int
    capacity: int
    status: SectionStatusEnum


class SectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    section_id: int
    class_name: str
    period: str
    capacity: int
    status: SectionStatusEnum
    created_at: datetime


class SectionDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    section_id: int
    class_name: str
    teacher_name: Optional[str]
    period: str
    capacity: int
    enrolled_count: int
    status: SectionStatusEnum
    students: List[UserBrief]
    assignments: List[AssignmentBrief]
    quests: List[QuestBrief]


class SectionUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    section_id: int
    status: SectionStatusEnum
    updated_at: datetime
