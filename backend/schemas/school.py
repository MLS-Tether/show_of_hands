from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SchoolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    school_id: int
    name: str
    district: Optional[str] = None
    grades: Optional[str] = None
    created_at: datetime


class SchoolCodeResponse(BaseModel):
    school_code: str


class SchoolUpdate(BaseModel):
    name: Optional[str] = None
    district: Optional[str] = None
    grades: Optional[str] = None


class SchoolPointsResponse(BaseModel):
    total_points: int


class SchoolCreate(BaseModel):
    school_name: str
    admin_username: str
    admin_password: str
    admin_email: Optional[str] = None


class SchoolCreateResponse(BaseModel):
    school_id: int
    name: str
    school_code: str
    admin_user_id: int
    admin_username: str
    created_at: datetime
    access_token: str
    refresh_token: str
    token_type: str
