import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from db.pool import Base


class EnrollmentStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Enrollment(Base):
    __tablename__ = "enrollments"

    enrollment_id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey("sections.section_id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    status = Column(Enum(EnrollmentStatusEnum), nullable=False, default=EnrollmentStatusEnum.pending)
    is_archived = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    section = relationship("Section", back_populates="enrollments")
    student = relationship("User", foreign_keys=[student_id], back_populates="enrollments")
