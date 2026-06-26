from sqlalchemy import Column
from db.pool import Base


class Assignment(Base):
    __tablename__ = "assignments"
