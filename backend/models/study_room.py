from sqlalchemy import Column
from db.pool import Base


class StudyRoom(Base):
    __tablename__ = "study_rooms"
