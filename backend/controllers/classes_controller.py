from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from db.pool import get_db
from dependencies import require_role
from models.user_model import User
from models.class__model import Class_
from schemas.class_ import ClassResponse

router = APIRouter(prefix="/classes", tags=["classes"])


@router.get("", response_model=List[ClassResponse])
def list_classes(
    _: User = Depends(require_role(["teacher", "admin"])),
    db: Session = Depends(get_db),
):
    return db.query(Class_).order_by(Class_.name).all()
