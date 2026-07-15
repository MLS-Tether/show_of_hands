import enum
from datetime import datetime
from typing import List, Optional
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
    source_label: Optional[str] = None
    awarded_at: datetime


class PointBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    total_points: int
    transactions: List[PointTransactionResponse]
    page: int
    page_size: int
    total_count: int
