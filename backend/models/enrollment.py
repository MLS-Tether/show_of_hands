from sqlalchemy import Column
from db.pool import Base


class Enrollment(Base):
    __tablename__ = "enrollments"
