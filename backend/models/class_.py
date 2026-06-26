from sqlalchemy import Column
from db.pool import Base


class Class(Base):
    __tablename__ = "classes"
