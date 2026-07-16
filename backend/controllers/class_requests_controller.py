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
        subject=body.subject,
        description=body.description,
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
    requests = (
        db.query(ClassRequest)
        .filter(ClassRequest.school_id == current_user.school_id)
        .order_by(ClassRequest.created_at.desc())
        .all()
    )

    # Existing catalog is small and global (Class_.name has no school scoping
    # elsewhere in this app either), so one fetch + an in-Python substring
    # check in both directions is simpler and more correct than a single-
    # direction SQL ilike, which would miss e.g. "AP Biology" vs "Biology".
    existing_names = [name for (name,) in db.query(Class_.name).all()]

    results = []
    for req in requests:
        requested_lower = req.class_name.lower()
        similar = [
            name
            for name in existing_names
            if requested_lower in name.lower() or name.lower() in requested_lower
        ]
        results.append(
            ClassRequestListResponse(
                class_request_id=req.class_request_id,
                class_name=req.class_name,
                subject=req.subject,
                description=req.description,
                requested_by=req.requested_by,
                status=req.status,
                created_at=req.created_at,
                similar_classes=similar,
            )
        )
    return results


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
