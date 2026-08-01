from sqlalchemy.orm import Session

from models.inventory_model import InventoryItem
from models.shop_item_model import ShopItem, ShopItemTypeEnum
from models.user_model import User, RoleEnum

# Teachers/admins get every existing cosmetic auto-unlocked, no purchase
# required. Badges are excluded -- they're earned via the per-student
# badge-rule engine (services/badge_rules.py), which has no analog for staff.
AUTO_UNLOCK_TYPES = (ShopItemTypeEnum.avatar_base, ShopItemTypeEnum.avatar_accessory, ShopItemTypeEnum.theme)


def grant_cosmetics_to_staff_member(db: Session, user: User) -> None:
    """Idempotently grants one staff member ownership of every non-archived
    auto-unlock-eligible ShopItem they don't already own. Safe to call
    unconditionally regardless of role -- no-ops for students."""
    if user.role not in (RoleEnum.teacher, RoleEnum.admin):
        return

    owned_item_ids = {
        item_id for (item_id,) in db.query(InventoryItem.item_id).filter(
            InventoryItem.student_id == user.user_id,
        ).all()
    }

    query = db.query(ShopItem).filter(
        ShopItem.is_archived == False,
        ShopItem.item_type.in_(AUTO_UNLOCK_TYPES),
    )
    if owned_item_ids:
        query = query.filter(~ShopItem.item_id.in_(owned_item_ids))
    missing_items = query.all()

    for item in missing_items:
        db.add(InventoryItem(student_id=user.user_id, item_id=item.item_id, is_equipped=False))


def grant_item_to_all_staff(db: Session, item: ShopItem) -> None:
    """Backfills a newly-created auto-unlock-eligible ShopItem into every
    existing teacher/admin's inventory. ShopItem has no school scoping, so
    the catalog (and this grant) is global, matching existing behavior."""
    if item.item_type not in AUTO_UNLOCK_TYPES or item.is_archived:
        return

    staff_ids = [
        uid for (uid,) in db.query(User.user_id).filter(
            User.role.in_((RoleEnum.teacher, RoleEnum.admin)),
            User.is_archived == False,
        ).all()
    ]
    if not staff_ids:
        return

    already_owned_ids = {
        uid for (uid,) in db.query(InventoryItem.student_id).filter(
            InventoryItem.item_id == item.item_id,
            InventoryItem.student_id.in_(staff_ids),
        ).all()
    }

    for uid in staff_ids:
        if uid not in already_owned_ids:
            db.add(InventoryItem(student_id=uid, item_id=item.item_id, is_equipped=False))


def backfill_all_staff_inventories() -> None:
    """One-off startup backfill for teacher/admin accounts that predate this
    feature. Idempotent -- safe to call on every app start."""
    from db.pool import SessionLocal

    db = SessionLocal()
    try:
        staff = db.query(User).filter(
            User.role.in_((RoleEnum.teacher, RoleEnum.admin)),
            User.is_archived == False,
        ).all()
        for user in staff:
            grant_cosmetics_to_staff_member(db, user)
        db.commit()
    finally:
        db.close()
