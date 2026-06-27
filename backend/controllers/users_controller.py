from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.pool import get_db
from dependencies import get_current_user, require_role
from models.enrollment_model import Enrollment, EnrollmentStatusEnum
from models.notification_model import Notification, NotificationTypeEnum
from models.section_model import Section, SectionStatusEnum
from models.user_model import User, RoleEnum
from schemas.user import UserResponse, UserListResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserListResponse])
def list_users(
    role: Optional[str] = None,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter(
        User.school_id == current_user.school_id,
        User.is_archived == False,
    )
    if role:
        try:
            role_enum = RoleEnum(role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
        query = query.filter(User.role == role_enum)
    return query.order_by(User.created_at.desc()).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == RoleEnum.student and current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Students can only view their own profile.")

    user = db.query(User).filter(
        User.user_id == user_id,
        User.is_archived == False,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Cannot access users outside your school.")
    return user


@router.patch("/{user_id}/verify")
def verify_user(
    user_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.user_id == user_id,
        User.school_id == current_user.school_id,
        User.is_archived == False,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_verified = True
    db.commit()
    return {"message": "User verified successfully."}


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")

    user = db.query(User).filter(
        User.user_id == user_id,
        User.school_id == current_user.school_id,
        User.is_archived == False,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_archived = True
    user.deleted_at = datetime.now(timezone.utc)

    if user.role == RoleEnum.teacher:
        sections = db.query(Section).filter(
            Section.teacher_id == user_id,
            Section.is_archived == False,
        ).all()
        for section in sections:
            section.status = SectionStatusEnum.pending_reassignment
            enrollments = db.query(Enrollment).filter(
                Enrollment.section_id == section.section_id,
                Enrollment.status == EnrollmentStatusEnum.approved,
                Enrollment.is_archived == False,
            ).all()
            for enrollment in enrollments:
                db.add(Notification(
                    user_id=enrollment.student_id,
                    type=NotificationTypeEnum.section_status,
                    message=f"Section #{section.section_id} is pending teacher reassignment.",
                ))

    db.commit()
    return {"message": "User deleted successfully."}
