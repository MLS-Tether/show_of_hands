import enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ShopItemTypeEnum(str, enum.Enum):
    avatar_base = "avatar_base"
    avatar_accessory = "avatar_accessory"
    badge = "badge"
    theme = "theme"


class ShopItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    item_type: ShopItemTypeEnum
    cost: int
    image_url: str
    theme_key: Optional[str] = None


class ShopItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cost: Optional[int] = None
    image_url: Optional[str] = None
    theme_key: Optional[str] = None


class BadgeProgressResponse(BaseModel):
    current: float
    target: float
    unit: str


class ShopItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: int
    name: str
    description: Optional[str]
    item_type: ShopItemTypeEnum
    cost: int
    image_url: str
    theme_key: Optional[str]
    created_at: datetime
    owned: Optional[bool] = None
    equipped: Optional[bool] = None
    progress: Optional[BadgeProgressResponse] = None