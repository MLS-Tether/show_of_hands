from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from db.pool import Base


class QuestCompletion(Base):
    __tablename__ = "quest_completions"

    quest_completion_id = Column(Integer, primary_key=True)
    quest_id = Column(Integer, ForeignKey("quests.quest_id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    points_awarded = Column(Integer, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    quest = relationship("Quest", back_populates="quest_completions")
    student = relationship("User", foreign_keys=[student_id], back_populates="quest_completions")
