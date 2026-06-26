from sqlalchemy import Column
from db.pool import Base


class ClassRequest(Base):
    __tablename__ = "class_requests"
