import enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SubmissionStatusEnum(str, enum.Enum):
    submitted = "submitted"
    pending = "pending"
    graded = "graded"


class SubmissionCreate(BaseModel):
    content: Optional[str] = None
    file_url: Optional[str] = None
    completion: Optional[bool] = None


class SubmissionGradeUpdate(BaseModel):
    grade: float


class SubmissionCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    submission_id: int
    assignment_id: int
    student_id: int
    status: SubmissionStatusEnum
    points_awarded: int
    submitted_at: datetime = Field(validation_alias="created_at")


class SubmissionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    submission_id: int
    student_id: int
    username: str
    status: SubmissionStatusEnum
    grade: Optional[float]
    points_awarded: int
    submitted_at: datetime = Field(validation_alias="created_at")


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    submission_id: int
    assignment_id: int
    student_id: int
    content: Optional[str]
    file_url: Optional[str]
    status: SubmissionStatusEnum
    grade: Optional[float]
    points_awarded: int
    finalized_at: Optional[datetime]
    submitted_at: datetime = Field(validation_alias="created_at")


class SubmissionGradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    submission_id: int
    grade: float
    status: SubmissionStatusEnum
    updated_at: datetime


class SubmissionFinalizeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    submission_id: int
    grade: float
    status: SubmissionStatusEnum
    points_awarded: int
    finalized_at: datetime
