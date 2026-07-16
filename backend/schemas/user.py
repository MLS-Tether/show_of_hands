import enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class RoleEnum(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class UserCreate(BaseModel):
    username: str
    password: str
    school_code: str
    role: RoleEnum
    email: Optional[str] = None


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    role: RoleEnum
    school_id: int
    total_points: int
    created_at: datetime


class UserListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: Optional[str] = None
    role: RoleEnum
    is_verified: bool
    is_active: bool
    rejection_reason: Optional[str] = None
    signup_note: Optional[str] = None
    total_points: int
    last_active_at: Optional[datetime] = None
    created_at: datetime


class StudentSectionGradeResponse(BaseModel):
    section_id: int
    class_name: str
    period: str
    percentage: Optional[float]
    letter_grade: Optional[str]
