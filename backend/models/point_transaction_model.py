import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from db.pool import Base


class TransactionSourceEnum(str, enum.Enum):
    assignment = "assignment"
    quest = "quest"
    help_request = "help_request"


class PointTransaction(Base):
    __tablename__ = "point_transactions"

    transaction_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    amount = Column(Integer, nullable=False)
    source = Column(Enum(TransactionSourceEnum), nullable=False)
    source_id = Column(Integer, nullable=False)
    awarded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="point_transactions")
