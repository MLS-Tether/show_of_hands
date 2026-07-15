import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from db.pool import Base


class NotificationTypeEnum(str, enum.Enum):
    enrollment_approved = "enrollment_approved"
    enrollment_rejected = "enrollment_rejected"
    new_assignment = "new_assignment"
    new_quest = "new_quest"
    new_help_request = "new_help_request"
    help_request_accepted = "help_request_accepted"
    section_status = "section_status"
    class_request_approved = "class_request_approved"
    class_request_rejected = "class_request_rejected"
    grade_finalization_reminder = "grade_finalization_reminder"
    assignment_overdue = "assignment_overdue"
    new_help_request = "new_help_request"


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    type = Column(Enum(NotificationTypeEnum), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    assignment_id = Column(Integer, ForeignKey("assignments.assignment_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="notifications")
