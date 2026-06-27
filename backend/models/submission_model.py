import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from db.pool import Base


class SubmissionStatusEnum(str, enum.Enum):
    submitted = "submitted"
    pending = "pending"
    graded = "graded"


class Submission(Base):
    __tablename__ = "submissions"

    submission_id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.assignment_id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    content = Column(Text, nullable=True)
    file_url = Column(String, nullable=True)
    status = Column(Enum(SubmissionStatusEnum), nullable=False, default=SubmissionStatusEnum.submitted)
    grade = Column(Float, nullable=True)
    points_awarded = Column(Integer, nullable=False, default=0)
    finalized_at = Column(DateTime(timezone=True), nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User", foreign_keys=[student_id], back_populates="submissions")
