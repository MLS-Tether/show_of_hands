from datetime import datetime
from pydantic import BaseModel, ConfigDict

from schemas.shop_item import ShopItemResponse


class InventoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inventory_id: int
    item: ShopItemResponse
    is_equipped: bool
    purchased_at: datetime


class PurchaseResponse(BaseModel):
    inventory_id: int
    item_id: int
    points_spent: int
    total_points: int


class EquipRequest(BaseModel):
    equipped: bool