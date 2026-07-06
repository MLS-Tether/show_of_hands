from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from db.pool import Base


class School(Base):
    __tablename__ = "schools"

    school_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    school_code = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="school")
    sections = relationship("Section", back_populates="school")
    class_requests = relationship("ClassRequest", back_populates="school")
