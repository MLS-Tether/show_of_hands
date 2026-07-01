from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.pool import get_db
from dependencies import get_current_user, require_role
from models.enrollment_model import Enrollment, EnrollmentStatusEnum
from models.notification_model import Notification, NotificationTypeEnum
from models.section_model import Section
from models.user_model import User, RoleEnum
from schemas.enrollment import (
    EnrollmentRequestResponse,
    EnrollmentListResponse,
    EnrollmentStatusUpdate,
)

router = APIRouter(tags=["enrollment-requests"])


def _get_section_or_404(section_id: int, school_id: int, db: Session) -> Section:
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    return section


@router.post("/sections/{section_id}/enrollment-requests", response_model=EnrollmentRequestResponse, status_code=201)
def request_enrollment(
    section_id: int,
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db),
):
    section = _get_section_or_404(section_id, current_user.school_id, db)

    existing = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.student_id == current_user.user_id,
        Enrollment.is_archived == False,
    ).first()
    if existing:
        if existing.status == EnrollmentStatusEnum.approved:
            raise HTTPException(status_code=409, detail="Already enrolled in this section.")
        if existing.status == EnrollmentStatusEnum.pending:
            raise HTTPException(status_code=409, detail="Enrollment request already pending.")

    approved_count = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.status == EnrollmentStatusEnum.approved,
        Enrollment.is_archived == False,
    ).count()
    if approved_count >= section.capacity:
        raise HTTPException(status_code=409, detail="Section is at capacity.")

    enrollment = Enrollment(
        section_id=section_id,
        student_id=current_user.user_id,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


@router.get("/sections/{section_id}/enrollment-requests", response_model=List[EnrollmentListResponse])
def list_enrollment_requests(
    section_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (RoleEnum.teacher, RoleEnum.admin):
        raise HTTPException(status_code=403, detail="Unauthorized.")

    section = _get_section_or_404(section_id, current_user.school_id, db)

    if current_user.role == RoleEnum.teacher and section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")

    enrollments = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.is_archived == False,
    ).all()

    return [
        {
            "enrollment_id": e.enrollment_id,
            "student_id": e.student_id,
            "username": e.student.username,
            "status": e.status,
            "created_at": e.created_at,
        }
        for e in enrollments
    ]


@router.patch("/enrollment-requests/{enrollment_id}", response_model=EnrollmentRequestResponse)
def update_enrollment_request(
    enrollment_id: int,
    body: EnrollmentStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (RoleEnum.teacher, RoleEnum.admin):
        raise HTTPException(status_code=403, detail="Unauthorized.")

    enrollment = db.query(Enrollment).filter(
        Enrollment.enrollment_id == enrollment_id,
        Enrollment.is_archived == False,
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment request not found.")
    if enrollment.status != EnrollmentStatusEnum.pending:
        raise HTTPException(status_code=409, detail="Enrollment request already processed.")

    section = _get_section_or_404(enrollment.section_id, current_user.school_id, db)

    if current_user.role == RoleEnum.teacher and section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")

    if body.status == "approved":
        approved_count = db.query(Enrollment).filter(
            Enrollment.section_id == enrollment.section_id,
            Enrollment.status == EnrollmentStatusEnum.approved,
            Enrollment.is_archived == False,
        ).count()
        if approved_count >= section.capacity:
            raise HTTPException(status_code=409, detail="Section is at capacity.")
        enrollment.status = EnrollmentStatusEnum.approved
        notification_type = NotificationTypeEnum.enrollment_approved
        message = f"Your enrollment request for {section.class_.name} has been approved."
    else:
        enrollment.status = EnrollmentStatusEnum.rejected
        notification_type = NotificationTypeEnum.enrollment_rejected
        message = f"Your enrollment request for {section.class_.name} has been rejected."

    db.add(Notification(
        user_id=enrollment.student_id,
        type=notification_type,
        message=message,
    ))

    db.commit()
    db.refresh(enrollment)
    return enrollment


@router.delete("/sections/{section_id}/enrollments/{student_id}")
def drop_student(
    section_id: int,
    student_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    _get_section_or_404(section_id, current_user.school_id, db)

    enrollment = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.student_id == student_id,
        Enrollment.status == EnrollmentStatusEnum.approved,
        Enrollment.is_archived == False,
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found.")

    enrollment.is_archived = True
    enrollment.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Student dropped from section successfully."}
