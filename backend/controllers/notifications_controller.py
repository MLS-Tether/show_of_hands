from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.pool import get_db
from dependencies import get_current_user, require_role
from models.enrollment_model import Enrollment, EnrollmentStatusEnum
from models.notification_model import Notification, NotificationTypeEnum
from models.section_model import Section
from models.user_model import User
from schemas.notification import NotificationResponse, NotificationReadResponse

router = APIRouter(tags=["notifications"])


class SectionNotifyRequest(BaseModel):
    message: str


@router.get("/notifications", response_model=List[NotificationResponse])
def list_notifications(
    is_read: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
    )
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    return query.order_by(Notification.created_at.desc()).all()


# read-all MUST be registered before /{notification_id}/read to avoid path collision
@router.patch("/notifications/read-all")
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read."}


@router.patch("/notifications/{notification_id}/read", response_model=NotificationReadResponse)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.user_id == current_user.user_id,
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/sections/{section_id}/notify")
def notify_section(
    section_id: int,
    body: SectionNotifyRequest,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    enrolled = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.status == EnrollmentStatusEnum.approved,
        Enrollment.is_archived == False,
    ).all()

    for e in enrolled:
        db.add(Notification(
            user_id=e.student_id,
            type=NotificationTypeEnum.section_status,
            message=body.message,
        ))

    db.commit()
    return {"message": f"Notification sent to {len(enrolled)} student(s)."}
