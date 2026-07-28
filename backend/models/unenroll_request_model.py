import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from db.pool import Base


class UnenrollRequestStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class UnenrollRequest(Base):
    __tablename__ = "unenroll_requests"

    unenroll_request_id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey("sections.section_id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    requested_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(Enum(UnenrollRequestStatusEnum), nullable=False, default=UnenrollRequestStatusEnum.pending)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    section = relationship("Section")
    student = relationship("User", foreign_keys=[student_id])
    requester = relationship("User", foreign_keys=[requested_by])
