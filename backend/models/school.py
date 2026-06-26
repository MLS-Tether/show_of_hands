from sqlalchemy import Column
from db.pool import Base


class School(Base):
    __tablename__ = "schools"
