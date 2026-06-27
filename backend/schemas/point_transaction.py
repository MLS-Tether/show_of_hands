import enum
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict


class TransactionSourceEnum(str, enum.Enum):
    assignment = "assignment"
    quest = "quest"
    help_request = "help_request"


class PointTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: int
    amount: int
    source: TransactionSourceEnum
    source_id: int
    awarded_at: datetime


class PointBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    total_points: int
    transactions: List[PointTransactionResponse]
