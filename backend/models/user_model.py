import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from db.pool import Base


class RoleEnum(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.school_id"), nullable=False)
    username = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    email = Column(String, nullable=True)
    role = Column(Enum(RoleEnum), nullable=False)
    is_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    rejection_reason = Column(Text, nullable=True)
    last_active_at = Column(DateTime(timezone=True), nullable=True)
    signup_note = Column(Text, nullable=True)
    total_points = Column(Integer, nullable=False, default=0)
    is_archived = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    school = relationship("School", back_populates="users")
    sections_taught = relationship("Section", back_populates="teacher", foreign_keys="Section.teacher_id")
    enrollments = relationship("Enrollment", back_populates="student", foreign_keys="Enrollment.student_id")
    submissions = relationship("Submission", back_populates="student", foreign_keys="Submission.student_id")
    quests_assigned = relationship("Quest", back_populates="assigned_student", foreign_keys="Quest.assigned_to")
    quest_completions = relationship("QuestCompletion", back_populates="student", foreign_keys="QuestCompletion.student_id")
    point_transactions = relationship("PointTransaction", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    help_requests_made = relationship("HelpRequest", back_populates="requester", foreign_keys="HelpRequest.requester_id")
    help_request_acceptances = relationship("HelpRequestAcceptance", back_populates="user", foreign_keys="HelpRequestAcceptance.user_id")
    room_memberships = relationship("RoomMember", back_populates="user", foreign_keys="RoomMember.user_id")
