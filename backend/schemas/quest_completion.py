from datetime import datetime
from pydantic import BaseModel, ConfigDict


class QuestCompletionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quest_completion_id: int
    quest_id: int
    student_id: int
    points_awarded: int
    completed_at: datetime
