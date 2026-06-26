from sqlalchemy import Column
from db.pool import Base


class Section(Base):
    __tablename__ = "sections"
