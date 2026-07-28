from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from db.pool import Base


class InventoryItem(Base):
    __tablename__ = "student_inventory"
    __table_args__ = (
        UniqueConstraint("student_id", "item_id", name="uq_inventory_student_item"),
    )

    inventory_id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    item_id = Column(Integer, ForeignKey("shop_items.item_id"), nullable=False)
    is_equipped = Column(Boolean, nullable=False, default=False)
    purchased_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    student = relationship("User", back_populates="inventory_items")
    item = relationship("ShopItem", back_populates="inventory_entries")