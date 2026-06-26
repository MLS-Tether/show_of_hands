from sqlalchemy import Column
from db.pool import Base


class QuestCompletion(Base):
    __tablename__ = "quest_completions"
