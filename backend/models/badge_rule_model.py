import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Boolean, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from db.pool import Base


class BadgeRuleCriteriaEnum(str, enum.Enum):
    first_quest = "first_quest"
    quest_streak = "quest_streak"
    event_count = "event_count"
    lifetime_points = "lifetime_points"
    quest_total_count = "quest_total_count"
    section_grade_threshold = "section_grade_threshold"


class BadgeRule(Base):
    __tablename__ = "badge_rules"

    badge_rule_id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("shop_items.item_id"), nullable=False, unique=True)
    criteria_type = Column(Enum(BadgeRuleCriteriaEnum), nullable=False)
    threshold = Column(Integer, nullable=False)
    params = Column(JSON, nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    item = relationship("ShopItem")
