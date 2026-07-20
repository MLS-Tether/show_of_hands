import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from db.pool import Base


class SectionStatusEnum(str, enum.Enum):
    active = "active"
    archived = "archived"
    pending_reassignment = "pending_reassignment"


class Section(Base):
    __tablename__ = "sections"

    section_id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("classes.class_id"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.school_id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    period = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    status = Column(Enum(SectionStatusEnum), nullable=False, default=SectionStatusEnum.active)
    is_archived = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    class_ = relationship("Class_", back_populates="sections")
    school = relationship("School", back_populates="sections")
    teacher = relationship("User", foreign_keys=[teacher_id], back_populates="sections_taught")
    enrollments = relationship("Enrollment", back_populates="section")
    assignments = relationship("Assignment", back_populates="section")
    quests = relationship("Quest", back_populates="section")
    help_requests = relationship("HelpRequest", back_populates="section")
    resources = relationship("Resource", back_populates="section")
