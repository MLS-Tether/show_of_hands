from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.pool import get_db
from dependencies import get_current_user, require_role
from models.user_model import User
from models.section_model import Section
from models.enrollment_model import Enrollment, EnrollmentRequest
from models.notification_model import Notification
from schemas.enrollment import (
    EnrollmentRequestCreateResponse,
    EnrollmentRequestListItem,
    EnrollmentRequestUpdate,
    EnrollmentRequestUpdateResponse,
    MessageResponse,
)

router = APIRouter(prefix="/api", tags=["enrollment-requests"])

@router.post(
    "/sections/{section_id}/enrollment-requests",
    response_model=EnrollmentRequestCreateResponse,
    status_code=201,
)
def create_enrollment_request(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    section = (
        db.query(Section)
        .filter(Section.section_id == section_id, Section.is_archived == False)  # noqa: E712
        .first()
    )
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    already_enrolled = (
        db.query(Enrollment)
        .filter(
            Enrollment.section_id == section_id,
            Enrollment.student_id == current_user.user_id,
            Enrollment.is_archived == False,  # noqa: E712
        )
        .first()
    )
    if already_enrolled:
        raise HTTPException(status_code=409, detail="Student already enrolled")

    existing_request = (
        db.query(EnrollmentRequest)
        .filter(
            EnrollmentRequest.section_id == section_id,
            EnrollmentRequest.student_id == current_user.user_id,
            EnrollmentRequest.status == "pending",
        )
        .first()
    )
    if existing_request:
        raise HTTPException(status_code=409, detail="Request already exists")

    new_request = EnrollmentRequest(
        section_id=section_id,
        student_id=current_user.user_id,
        status="pending",
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request) 

    return new_request

@router.get(
    "/sections/{section_id}/enrollment-requests",
    response_model=list[EnrollmentRequestListItem],
)
def get_enrollment_requests(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher", "admin")),
):
    section = db.query(Section).filter(Section.section_id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    if current_user.role == "teacher" and section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not the section owner")

    requests = (
        db.query(EnrollmentRequest)
        .filter(
            EnrollmentRequest.section_id == section_id,
            EnrollmentRequest.status == "pending",
        )
        .all()
    )

    return [
        EnrollmentRequestListItem(
            enrollment_request_id=r.enrollment_request_id,
            student_id=r.student_id,
            username=r.student.username,
            status=r.status,
            created_at=r.created_at,
        )
        for r in requests
    ]

@router.patch(
    "/enrollment-requests/{enrollment_request_id}",
    response_model=EnrollmentRequestUpdateResponse,
)
def update_enrollment_request(
    enrollment_request_id: int,
    body: EnrollmentRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    request = (
        db.query(EnrollmentRequest)
        .filter(EnrollmentRequest.enrollment_request_id == enrollment_request_id)
        .first()
    )
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    section = db.query(Section).filter(Section.section_id == request.section_id).first()
    if not section or section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not the section owner")

    request.status = body.status
    request.updated_at = datetime.now(timezone.utc)

    if body.status == "approved":
        db.add(Enrollment(section_id=request.section_id, student_id=request.student_id))
        db.add(
            Notification(
                user_id=request.student_id,
                type="enrollment_approved",
                message=f"Your request to join {section.period} was approved.",
            )
        )
    else:
        db.add(
            Notification(
                user_id=request.student_id,
                type="enrollment_rejected",
                message=f"Your request to join {section.period} was rejected.",
            )
        )

    db.commit()
    db.refresh(request)

    return EnrollmentRequestUpdateResponse(
        enrollment_request_id=request.enrollment_request_id,
        status=request.status,
    )

@router.delete(
    "/sections/{section_id}/students/{student_id}",
    response_model=MessageResponse,
)
def drop_student_from_section(
    section_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    enrollment = (
        db.query(Enrollment)
        .filter(
            Enrollment.section_id == section_id,
            Enrollment.student_id == student_id,
            Enrollment.is_archived == False,  
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    enrollment.is_archived = True
    enrollment.deleted_at = datetime.now(timezone.utc)
    db.commit()

    return MessageResponse(message="Student removed from section.")