from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.pool import get_db
from dependencies import get_current_user
from models.assignment_model import Assignment
from models.help_request_model import HelpRequest
from models.point_transaction_model import PointTransaction, TransactionSourceEnum
from models.quest_model import Quest
from models.user_model import User, RoleEnum
from schemas.point_transaction import PointBalanceResponse

_SOURCE_LOOKUPS = {
    TransactionSourceEnum.assignment: (Assignment, "assignment_id", "title"),
    TransactionSourceEnum.quest: (Quest, "quest_id", "title"),
    TransactionSourceEnum.help_request: (HelpRequest, "help_request_id", "topic"),
}

router = APIRouter(prefix="/users", tags=["points"])


@router.get("/{user_id}/points", response_model=PointBalanceResponse)
def get_user_points(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == RoleEnum.student and current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Students can only view their own points.")

    user = db.query(User).filter(
        User.user_id == user_id,
        User.is_archived == False,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Cannot access users outside your school.")

    query = db.query(PointTransaction).filter(PointTransaction.user_id == user_id)
    total_count = query.count()
    transactions = (
        query.order_by(PointTransaction.awarded_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    labels_by_source = {}
    for source, (model, pk_name, label_field) in _SOURCE_LOOKUPS.items():
        source_ids = [t.source_id for t in transactions if t.source == source]
        if not source_ids:
            continue
        rows = db.query(model).filter(getattr(model, pk_name).in_(source_ids)).all()
        labels_by_source[source] = {getattr(row, pk_name): getattr(row, label_field) for row in rows}

    return {
        "user_id": user.user_id,
        "total_points": user.total_points,
        "transactions": [
            {
                "transaction_id": t.transaction_id,
                "amount": t.amount,
                "source": t.source,
                "source_id": t.source_id,
                "source_label": labels_by_source.get(t.source, {}).get(t.source_id),
                "awarded_at": t.awarded_at,
            }
            for t in transactions
        ],
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
    }
