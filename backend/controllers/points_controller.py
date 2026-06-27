from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.pool import get_db
from dependencies import get_current_user
from models.user_model import User, RoleEnum
from schemas.point_transaction import PointBalanceResponse

router = APIRouter(prefix="/users", tags=["points"])


@router.get("/{user_id}/points", response_model=PointBalanceResponse)
def get_user_points(
    user_id: int,
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
            for t in user.point_transactions
        ],
    }
