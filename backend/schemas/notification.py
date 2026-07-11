import enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class NotificationTypeEnum(str, enum.Enum):
    enrollment_approved = "enrollment_approved"
    enrollment_rejected = "enrollment_rejected"
    new_assignment = "new_assignment"
    new_quest = "new_quest"
    help_request_accepted = "help_request_accepted"
    section_status = "section_status"
    class_request_approved = "class_request_approved"
    class_request_rejected = "class_request_rejected"
    grade_finalization_reminder = "grade_finalization_reminder"
    assignment_overdue = "assignment_overdue"
    new_help_request = "new_help_request"


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: int
    type: NotificationTypeEnum
    message: str
    is_read: bool
    assignment_id: Optional[int] = None
    created_at: datetime


class NotificationReadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: int
    is_read: bool
