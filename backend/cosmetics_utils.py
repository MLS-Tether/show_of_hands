from sqlalchemy.orm import Session

from models.inventory_model import InventoryItem
from models.shop_item_model import ShopItem, ShopItemTypeEnum


def get_equipped_cosmetics_for_users(db: Session, user_ids: list) -> dict:
    """Equipped avatar_base/avatar_accessory/badge items for each of the given
    user ids, keyed by user_id. Users with nothing equipped are absent from
    the returned dict. Themes are excluded (not rendered by CharacterAvatar)."""
    if not user_ids:
        return {}

    rows = (
        db.query(InventoryItem, ShopItem)
        .join(ShopItem, InventoryItem.item_id == ShopItem.item_id)
        .filter(
            InventoryItem.student_id.in_(user_ids),
            InventoryItem.is_equipped == True,
            ShopItem.item_type != ShopItemTypeEnum.theme,
        )
        .all()
    )

    cosmetics = {}
    for inventory_item, shop_item in rows:
        entry = cosmetics.setdefault(inventory_item.student_id, {"avatar_base": None, "avatar_accessory": None, "badges": []})
        brief = {"item_id": shop_item.item_id, "name": shop_item.name, "image_url": shop_item.image_url}
        if shop_item.item_type == ShopItemTypeEnum.avatar_base:
            entry["avatar_base"] = brief
        elif shop_item.item_type == ShopItemTypeEnum.avatar_accessory:
            entry["avatar_accessory"] = brief
        elif shop_item.item_type == ShopItemTypeEnum.badge:
            entry["badges"].append(brief)

    return cosmetics
