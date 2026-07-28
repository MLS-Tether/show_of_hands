from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class QuestCompletionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quest_completion_id: int
    quest_id: int
    student_id: int
    points_awarded: int
    completed_at: datetime
    description: Optional[str] = None
    file_url: Optional[str] = None


class QuestCompletionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quest_completion_id: int
    student_id: int
    username: str
    description: Optional[str] = None
    file_url: Optional[str] = None
    points_awarded: int
    completed_at: datetime
