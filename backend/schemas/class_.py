from pydantic import BaseModel, ConfigDict


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    class_id: int
    name: str
