import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from db.pool import Base


class ClassRequestStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ClassRequest(Base):
    __tablename__ = "class_requests"

    class_request_id = Column(Integer, primary_key=True)
    class_name = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    requested_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.school_id"), nullable=False)
    status = Column(Enum(ClassRequestStatusEnum), nullable=False, default=ClassRequestStatusEnum.pending)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    requester = relationship("User", foreign_keys=[requested_by])
    school = relationship("School", back_populates="class_requests")
