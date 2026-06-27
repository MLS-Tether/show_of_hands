import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from db.pool import Base


class StudyRoomStatusEnum(str, enum.Enum):
    active = "active"
    closed = "closed"


class StudyRoom(Base):
    __tablename__ = "study_rooms"

    room_id = Column(Integer, primary_key=True)
    help_request_id = Column(Integer, ForeignKey("help_requests.help_request_id"), nullable=False, unique=True)
    timer_ends_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(StudyRoomStatusEnum), nullable=False, default=StudyRoomStatusEnum.active)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    help_request = relationship("HelpRequest", back_populates="study_room")
    members = relationship("RoomMember", back_populates="room")


class RoomMember(Base):
    __tablename__ = "room_members"

    room_id = Column(Integer, ForeignKey("study_rooms.room_id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    joined_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    room = relationship("StudyRoom", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="room_memberships")
