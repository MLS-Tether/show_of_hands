import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from db.pool import Base


class HelpRequestStatusEnum(str, enum.Enum):
    open = "open"
    active = "active"
    closed = "closed"
    expired = "expired"


class HelpRequest(Base):
    __tablename__ = "help_requests"

    help_request_id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey("sections.section_id"), nullable=False)
    requester_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    topic = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    group_size = Column(Integer, nullable=False)
    current_size = Column(Integer, nullable=False, default=1)
    duration_minutes = Column(Integer, nullable=False)
    status = Column(Enum(HelpRequestStatusEnum), nullable=False, default=HelpRequestStatusEnum.open)
    is_archived = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    section = relationship("Section", back_populates="help_requests")
    requester = relationship("User", foreign_keys=[requester_id], back_populates="help_requests_made")
    acceptances = relationship("HelpRequestAcceptance", back_populates="help_request")
    study_room = relationship("StudyRoom", back_populates="help_request", uselist=False)


class HelpRequestAcceptance(Base):
    __tablename__ = "help_request_acceptances"

    help_request_id = Column(Integer, ForeignKey("help_requests.help_request_id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    accepted_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    help_request = relationship("HelpRequest", back_populates="acceptances")
    user = relationship("User", foreign_keys=[user_id], back_populates="help_request_acceptances")
