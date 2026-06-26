from sqlalchemy import Column
from db.pool import Base


class Quest(Base):
    __tablename__ = "quests"
