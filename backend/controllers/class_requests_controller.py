from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from db.pool import get_db
from dependencies import require_role
from models.user_model import User
from models.class__model import Class_
from models.class_request_model import ClassRequest, ClassRequestStatusEnum
from models.notification_model import Notification, NotificationTypeEnum
from schemas.class_request import (
    ClassRequestCreate,
    ClassRequestUpdateStatus,
    ClassRequestResponse,
    ClassRequestListResponse,
    ClassRequestStatusResponse,
)

router = APIRouter(prefix="/class-requests", tags=["class-requests"])


@router.post("", response_model=ClassRequestResponse, status_code=201)
def create_class_request(
    body: ClassRequestCreate,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    req = ClassRequest(
        class_name=body.class_name,
        requested_by=current_user.user_id,
        school_id=current_user.school_id,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("", response_model=List[ClassRequestListResponse])
def list_class_requests(
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    return (
        db.query(ClassRequest)
        .filter(ClassRequest.school_id == current_user.school_id)
        .order_by(ClassRequest.created_at.desc())
        .all()
    )


@router.patch("/{class_request_id}", response_model=ClassRequestStatusResponse)
def update_class_request_status(
    class_request_id: int,
    body: ClassRequestUpdateStatus,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    req = db.query(ClassRequest).filter(
        ClassRequest.class_request_id == class_request_id,
        ClassRequest.school_id == current_user.school_id,
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Class request not found.")
    if req.status != ClassRequestStatusEnum.pending:
        raise HTTPException(status_code=409, detail="Class request already processed.")

    req.status = body.status

    if body.status == ClassRequestStatusEnum.approved:
        existing = db.query(Class_).filter(Class_.name == req.class_name).first()
        if not existing:
            db.add(Class_(name=req.class_name))
        notification_type = NotificationTypeEnum.class_request_approved
        notification_msg = f"Your class request for '{req.class_name}' has been approved."
    else:
        notification_type = NotificationTypeEnum.class_request_rejected
        notification_msg = f"Your class request for '{req.class_name}' has been rejected."

    db.add(Notification(
        user_id=req.requested_by,
        type=notification_type,
        message=notification_msg,
    ))
    db.commit()
    db.refresh(req)
    return req
