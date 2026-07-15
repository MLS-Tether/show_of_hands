from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.pool import get_db
from dependencies import get_current_user
from models.point_transaction_model import PointTransaction
from models.user_model import User, RoleEnum
from schemas.point_transaction import PointBalanceResponse

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

    return {
        "user_id": user.user_id,
        "total_points": user.total_points,
        "transactions": [
            {
                "transaction_id": t.transaction_id,
                "amount": t.amount,
                "source": t.source,
                "source_id": t.source_id,
                "awarded_at": t.awarded_at,
            }
            for t in transactions
        ],
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
    }
