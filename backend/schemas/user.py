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
    role: RoleEnum
    is_verified: bool
    created_at: datetime
