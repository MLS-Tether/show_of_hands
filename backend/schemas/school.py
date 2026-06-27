from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SchoolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    school_id: int
    name: str
    created_at: datetime


class SchoolCodeResponse(BaseModel):
    school_code: str
