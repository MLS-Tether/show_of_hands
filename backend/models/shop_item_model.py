import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from db.pool import Base


class ShopItemTypeEnum(str, enum.Enum):
    avatar_base = "avatar_base"
    avatar_accessory = "avatar_accessory"
    badge = "badge"
    theme = "theme"


class ShopItem(Base):
    __tablename__ = "shop_items"

    item_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    item_type = Column(Enum(ShopItemTypeEnum), nullable=False)
    cost = Column(Integer, nullable=False)
    image_url = Column(String, nullable=False)
    theme_key = Column(String, nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    inventory_entries = relationship("InventoryItem", back_populates="item")