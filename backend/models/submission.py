from sqlalchemy import Column
from db.pool import Base


class Submission(Base):
    __tablename__ = "submissions"
