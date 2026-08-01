from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.data_events import emit_data_event
from db.pool import get_db
from dependencies import get_current_user, require_role
from models.badge_rule_model import BadgeRule
from models.inventory_model import InventoryItem
from models.point_transaction_model import PointTransaction, TransactionSourceEnum
from models.shop_item_model import ShopItem, ShopItemTypeEnum
from models.user_model import User, RoleEnum
from schemas.inventory import InventoryItemResponse, PurchaseResponse, EquipRequest
from schemas.shop_item import ShopItemCreate, ShopItemUpdate, ShopItemResponse
from services.badge_rules import get_badge_progress
from services.staff_inventory import grant_item_to_all_staff

router = APIRouter(tags=["shop"])

SINGLE_EQUIP_TYPES = (ShopItemTypeEnum.avatar_base, ShopItemTypeEnum.avatar_accessory, ShopItemTypeEnum.theme)


@router.get("/shop/items", response_model=List[ShopItemResponse])
def list_shop_items(
    item_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ShopItem).filter(ShopItem.is_archived == False)
    if item_type is not None:
        try:
            item_type_enum = ShopItemTypeEnum(item_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid item_type: {item_type}")
        query = query.filter(ShopItem.item_type == item_type_enum)

    items = query.order_by(ShopItem.created_at.asc()).all()

    # Owned/equipped applies to every role now -- students via purchase or
    # badge-award, teachers/admins via the cosmetics auto-unlock grant
    # (services/staff_inventory.py). Badge progress stays student-only:
    # badges are never granted to staff, so it wouldn't mean anything there.
    owned_by_item_id = {
        inv.item_id: inv
        for inv in db.query(InventoryItem).filter(
            InventoryItem.student_id == current_user.user_id,
            InventoryItem.item_id.in_([i.item_id for i in items]),
        ).all()
    }
    for item in items:
        owned_row = owned_by_item_id.get(item.item_id)
        item.owned = owned_row is not None
        item.equipped = owned_row.is_equipped if owned_row else False

    if current_user.role == RoleEnum.student:
        badge_item_ids = [i.item_id for i in items if i.item_type == ShopItemTypeEnum.badge]
        rules_by_item_id = {
            r.item_id: r
            for r in db.query(BadgeRule).filter(
                BadgeRule.is_archived == False,
                BadgeRule.item_id.in_(badge_item_ids),
            ).all()
        } if badge_item_ids else {}

        for item in items:
            rule = rules_by_item_id.get(item.item_id)
            item.progress = get_badge_progress(db, current_user.user_id, rule) if rule else None

    return items


@router.post("/shop/items", response_model=ShopItemResponse, status_code=201)
def create_shop_item(
    body: ShopItemCreate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    item = ShopItem(**body.model_dump())
    db.add(item)
    db.flush()
    grant_item_to_all_staff(db, item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/shop/items/{item_id}", response_model=ShopItemResponse)
def update_shop_item(
    item_id: int,
    body: ShopItemUpdate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    item = db.query(ShopItem).filter(
        ShopItem.item_id == item_id,
        ShopItem.is_archived == False,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Shop item not found.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/shop/items/{item_id}")
def delete_shop_item(
    item_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    item = db.query(ShopItem).filter(
        ShopItem.item_id == item_id,
        ShopItem.is_archived == False,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Shop item not found.")

    item.is_archived = True
    db.commit()
    return {"message": "Shop item archived successfully."}


@router.post("/shop/items/{item_id}/purchase", response_model=PurchaseResponse)
def purchase_shop_item(
    item_id: int,
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db),
):
    item = db.query(ShopItem).filter(
        ShopItem.item_id == item_id,
        ShopItem.is_archived == False,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Shop item not found.")

    if item.item_type == ShopItemTypeEnum.badge:
        raise HTTPException(status_code=403, detail="Badges are earned automatically and cannot be purchased.")

    existing = db.query(InventoryItem).filter(
        InventoryItem.student_id == current_user.user_id,
        InventoryItem.item_id == item_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already owned.")

    if current_user.total_points < item.cost:
        raise HTTPException(status_code=409, detail="Not enough points.")

    inventory = InventoryItem(student_id=current_user.user_id, item_id=item.item_id, is_equipped=False)
    db.add(inventory)
    db.flush()

    db.add(PointTransaction(
        user_id=current_user.user_id,
        amount=-item.cost,
        source=TransactionSourceEnum.shop_purchase,
        source_id=item.item_id,
    ))
    current_user.total_points -= item.cost

    emit_data_event(db, "points", "updated", current_user.school_id, [current_user.user_id])
    emit_data_event(db, "inventory", "updated", current_user.school_id, [current_user.user_id])

    db.commit()
    db.refresh(inventory)

    return PurchaseResponse(
        inventory_id=inventory.inventory_id,
        item_id=item.item_id,
        points_spent=item.cost,
        total_points=current_user.total_points,
    )


@router.get("/users/{user_id}/inventory", response_model=List[InventoryItemResponse])
def get_user_inventory(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == RoleEnum.student and current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Students can only view their own inventory.")

    user = db.query(User).filter(
        User.user_id == user_id,
        User.is_archived == False,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Cannot access users outside your school.")

    return (
        db.query(InventoryItem)
        .filter(InventoryItem.student_id == user_id)
        .order_by(InventoryItem.purchased_at.desc())
        .all()
    )


@router.patch("/inventory/{inventory_id}/equip", response_model=InventoryItemResponse)
def equip_inventory_item(
    inventory_id: int,
    body: EquipRequest,
    current_user: User = Depends(require_role(["student", "teacher", "admin"])),
    db: Session = Depends(get_db),
):
    inventory = db.query(InventoryItem).filter(InventoryItem.inventory_id == inventory_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory item not found.")
    if inventory.student_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your item.")

    if body.equipped and inventory.item.item_type in SINGLE_EQUIP_TYPES:
        siblings = db.query(InventoryItem).join(ShopItem, InventoryItem.item_id == ShopItem.item_id).filter(
            InventoryItem.student_id == current_user.user_id,
            ShopItem.item_type == inventory.item.item_type,
            InventoryItem.inventory_id != inventory.inventory_id,
        ).all()
        for sibling in siblings:
            sibling.is_equipped = False

    inventory.is_equipped = body.equipped

    emit_data_event(db, "inventory", "updated", current_user.school_id, [current_user.user_id])

    db.commit()
    db.refresh(inventory)
    return inventory