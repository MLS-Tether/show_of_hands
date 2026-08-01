import enum
from datetime import datetime
from typing import List, Optional
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


class FeaturedBadgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: int
    name: str
    image_url: str


class FeaturedBadgeUpdateRequest(BaseModel):
    item_id: Optional[int] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    full_name: str
    profile_picture_url: Optional[str] = None
    role: RoleEnum
    school_id: int
    total_points: int
    featured_badge: Optional[FeaturedBadgeResponse] = None
    created_at: datetime


class UserListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    full_name: str
    profile_picture_url: Optional[str] = None
    email: Optional[str] = None
    role: RoleEnum
    is_verified: bool
    is_active: bool
    rejection_reason: Optional[str] = None
    signup_note: Optional[str] = None
    total_points: int
    last_active_at: Optional[datetime] = None
    created_at: datetime


class ProfileUpdateRequest(BaseModel):
    username: Optional[str] = None


class ProfilePictureResponse(BaseModel):
    profile_picture_url: Optional[str] = None


class StudentSectionGradeResponse(BaseModel):
    section_id: int
    class_name: str
    period: str
    percentage: Optional[float]
    letter_grade: Optional[str]


class ReportCardItemResponse(BaseModel):
    kind: str
    item_id: int
    name: str
    category: str
    assigned_at: datetime
    grade: Optional[float] = None


class ReportCardSectionResponse(BaseModel):
    section_id: int
    class_name: str
    period: str
    teacher_name: Optional[str]
    percentage: Optional[float]
    letter_grade: Optional[str]
    items: List["ReportCardItemResponse"]


class ReportCardResponse(BaseModel):
    student_id: int
    username: str
    full_name: str
    sections: List["ReportCardSectionResponse"]
