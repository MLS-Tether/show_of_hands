import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from db.pool import Base


class QuestCategoryEnum(str, enum.Enum):
    academic = "academic"
    social = "social"


class QuestTypeEnum(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class QuestSourceEnum(str, enum.Enum):
    teacher = "teacher"
    system = "system"


class Quest(Base):
    __tablename__ = "quests"

    quest_id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey("sections.section_id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Enum(QuestCategoryEnum), nullable=False)
    point_value = Column(Integer, nullable=False)
    quest_type = Column(Enum(QuestTypeEnum), nullable=False)
    source = Column(Enum(QuestSourceEnum), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    section = relationship("Section", back_populates="quests")
    assigned_student = relationship("User", foreign_keys=[assigned_to], back_populates="quests_assigned")
    quest_completions = relationship("QuestCompletion", back_populates="quest")
