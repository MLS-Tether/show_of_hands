from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel

from gemini_advisor import FitVerdict
from models.assignment_model import AssignmentCategoryEnum


class AssignmentDraft(BaseModel):
    title: str
    description: Optional[str] = None
    category: AssignmentCategoryEnum
    point_value: int
    due_date: datetime


class AssignmentFitResponse(BaseModel):
    ai_available: bool
    unavailable_reason: Optional[str] = None  # "not_configured" | "insufficient_data" | "error"
    verdict: Optional[FitVerdict] = None
    stats: Dict[str, Any]
