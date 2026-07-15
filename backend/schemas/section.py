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
    teacher_id: Optional[int]
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
    created_at: datetime
    students: List[UserBrief]
    assignments: List[AssignmentBrief]
    quests: List[QuestBrief]


class SectionUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    section_id: int
    status: SectionStatusEnum
    updated_at: datetime


class AssignmentAnalytics(BaseModel):
    assignment_id: int
    title: str
    point_value: int
    submitted_count: int
    graded_count: int
    average_grade: Optional[float]
    completion_rate: float


class PointsDistribution(BaseModel):
    min: Optional[int]
    max: Optional[int]
    median: Optional[float]


class StudentNeedingAttention(BaseModel):
    user_id: int
    username: str
    reason: str
    assignment_id: int
    assignment_title: Optional[str] = None
    grade: Optional[float] = None


class SectionAnalyticsResponse(BaseModel):
    section_id: int
    enrolled_count: int
    assignment_count: int
    average_grade: Optional[float]
    assignments: List[AssignmentAnalytics]
    points_distribution: PointsDistribution
    students_needing_attention: List[StudentNeedingAttention]
