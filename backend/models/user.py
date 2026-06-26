from sqlalchemy import Column
from db.pool import Base


class User(Base):
    __tablename__ = "users"
