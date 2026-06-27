import enum
from datetime import datetime
from typing import Optional, Union, Literal
from pydantic import BaseModel, ConfigDict, field_validator


class QuestCategoryEnum(str, enum.Enum):
    academic = "academic"
    social = "social"


class QuestTypeEnum(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class QuestSourceEnum(str, enum.Enum):
    teacher = "teacher"
    system = "system"


class QuestCreate(BaseModel):
    title: str
    description: str
    category: QuestCategoryEnum
    point_value: int
    quest_type: QuestTypeEnum
    assigned_to: Union[Literal["all"], int]


class QuestBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quest_id: int
    title: str
    category: QuestCategoryEnum


class QuestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quest_id: int
    title: str
    description: str
    category: QuestCategoryEnum
    point_value: int
    quest_type: QuestTypeEnum
    source: QuestSourceEnum
    assigned_to: Union[Literal["all"], int]
    created_at: datetime

    @field_validator("assigned_to", mode="before")
    @classmethod
    def coerce_assigned_to(cls, v: Optional[int]) -> Union[Literal["all"], int]:
        if v is None:
            return "all"
        return v


class QuestCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quest_id: int
    title: str
    category: QuestCategoryEnum
    point_value: int
    assigned_to: Union[Literal["all"], int]
    created_at: datetime

    @field_validator("assigned_to", mode="before")
    @classmethod
    def coerce_assigned_to(cls, v: Optional[int]) -> Union[Literal["all"], int]:
        if v is None:
            return "all"
        return v
