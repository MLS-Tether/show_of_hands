from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.data_events import emit_data_event, resolve_admin_ids, resolve_section_audience
from db.pool import get_db
from dependencies import require_role
from models.user_model import User
from models.section_model import Section
from models.enrollment_model import Enrollment
from models.unenroll_request_model import UnenrollRequest, UnenrollRequestStatusEnum
from models.notification_model import NotificationTypeEnum
from notifications import notify
from controllers.enrollment_requests_controller import archive_enrollment
from schemas.unenroll_request import (
    UnenrollRequestCreate,
    UnenrollRequestListItem,
    UnenrollRequestUpdateStatus,
    UnenrollRequestStatusResponse,
    MessageResponse,
)

router = APIRouter(tags=["unenroll-requests"])


@router.post(
    "/sections/{section_id}/unenroll-requests",
    response_model=UnenrollRequestListItem,
    status_code=201,
)
def create_unenroll_request(
    section_id: int,
    body: UnenrollRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    section = (
        db.query(Section)
        .filter(Section.section_id == section_id, Section.school_id == current_user.school_id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    if section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")

    enrollment = (
        db.query(Enrollment)
        .filter(
            Enrollment.section_id == section_id,
            Enrollment.student_id == body.student_id,
            Enrollment.is_archived == False,  # noqa: E712
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found.")

    existing_request = (
        db.query(UnenrollRequest)
        .filter(
            UnenrollRequest.section_id == section_id,
            UnenrollRequest.student_id == body.student_id,
            UnenrollRequest.status == UnenrollRequestStatusEnum.pending,
        )
        .first()
    )
    if existing_request:
        raise HTTPException(status_code=409, detail="A removal request for this student is already pending.")

    request = UnenrollRequest(
        section_id=section_id,
        student_id=body.student_id,
        requested_by=current_user.user_id,
        reason=body.reason,
    )
    db.add(request)
    db.flush()

    notify(
        db,
        resolve_admin_ids(db, current_user.school_id),
        NotificationTypeEnum.new_unenroll_request,
        f"{current_user.full_name} ({current_user.username}) requested removing {enrollment.student.username} from {section.period}.",
        entity_type="unenroll_request",
        entity_id=request.unenroll_request_id,
    )
    emit_data_event(
        db, "unenroll_requests", "created", section.school_id,
        resolve_admin_ids(db, section.school_id),
        section_id=section_id,
    )
    db.commit()
    db.refresh(request)

    return UnenrollRequestListItem(
        unenroll_request_id=request.unenroll_request_id,
        section_id=request.section_id,
        student_id=request.student_id,
        student_username=enrollment.student.username,
        requested_by=request.requested_by,
        requester_username=current_user.username,
        reason=request.reason,
        status=request.status,
        created_at=request.created_at,
    )


@router.get(
    "/sections/{section_id}/unenroll-requests",
    response_model=list[UnenrollRequestListItem],
)
def list_section_unenroll_requests(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["teacher", "admin"])),
):
    section = (
        db.query(Section)
        .filter(Section.section_id == section_id, Section.school_id == current_user.school_id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    if current_user.role == "teacher" and section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")

    requests = (
        db.query(UnenrollRequest)
        .filter(
            UnenrollRequest.section_id == section_id,
            UnenrollRequest.status == UnenrollRequestStatusEnum.pending,
        )
        .all()
    )
    return [
        UnenrollRequestListItem(
            unenroll_request_id=r.unenroll_request_id,
            section_id=r.section_id,
            student_id=r.student_id,
            student_username=r.student.username,
            requested_by=r.requested_by,
            requester_username=r.requester.username,
            reason=r.reason,
            status=r.status,
            created_at=r.created_at,
        )
        for r in requests
    ]


@router.get(
    "/unenroll-requests",
    response_model=list[UnenrollRequestListItem],
)
def list_unenroll_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    requests = (
        db.query(UnenrollRequest)
        .join(Section, Section.section_id == UnenrollRequest.section_id)
        .filter(Section.school_id == current_user.school_id)
        .order_by(UnenrollRequest.created_at.desc())
        .all()
    )
    return [
        UnenrollRequestListItem(
            unenroll_request_id=r.unenroll_request_id,
            section_id=r.section_id,
            student_id=r.student_id,
            student_username=r.student.username,
            requested_by=r.requested_by,
            requester_username=r.requester.username,
            reason=r.reason,
            status=r.status,
            created_at=r.created_at,
        )
        for r in requests
    ]


@router.patch(
    "/unenroll-requests/{unenroll_request_id}",
    response_model=UnenrollRequestStatusResponse,
)
def update_unenroll_request(
    unenroll_request_id: int,
    body: UnenrollRequestUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    request = (
        db.query(UnenrollRequest)
        .filter(UnenrollRequest.unenroll_request_id == unenroll_request_id)
        .first()
    )
    if not request:
        raise HTTPException(status_code=404, detail="Request not found.")
    if request.status != UnenrollRequestStatusEnum.pending:
        raise HTTPException(status_code=409, detail="Request already resolved.")

    section = db.query(Section).filter(
        Section.section_id == request.section_id,
        Section.school_id == current_user.school_id,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    request.status = body.status
    request.updated_at = datetime.now(timezone.utc)

    if body.status == UnenrollRequestStatusEnum.approved:
        enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.section_id == request.section_id,
                Enrollment.student_id == request.student_id,
                Enrollment.is_archived == False,  # noqa: E712
            )
            .first()
        )
        if not enrollment:
            raise HTTPException(status_code=409, detail="Student is no longer enrolled in this section.")
        archive_enrollment(enrollment)
        notify(
            db,
            request.student_id,
            NotificationTypeEnum.removed_from_section,
            f"You have been removed from {section.period}.",
            entity_type="section",
            entity_id=section.section_id,
        )
        notify(
            db,
            request.requested_by,
            NotificationTypeEnum.unenroll_request_approved,
            f"Your request to remove a student from {section.period} was approved.",
            entity_type="section",
            entity_id=section.section_id,
        )
        audience = resolve_section_audience(db, section)
        audience.append(request.student_id)
        emit_data_event(
            db, "sections", "updated", section.school_id, audience,
            section_id=section.section_id,
        )
    else:
        notify(
            db,
            request.requested_by,
            NotificationTypeEnum.unenroll_request_rejected,
            f"Your request to remove a student from {section.period} was rejected.",
            entity_type="section",
            entity_id=section.section_id,
        )

    db.commit()
    db.refresh(request)

    return UnenrollRequestStatusResponse(
        unenroll_request_id=request.unenroll_request_id,
        status=request.status,
    )


@router.post(
    "/unenroll-requests/{unenroll_request_id}/cancel",
    response_model=MessageResponse,
)
def cancel_unenroll_request(
    unenroll_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    request = (
        db.query(UnenrollRequest)
        .filter(UnenrollRequest.unenroll_request_id == unenroll_request_id)
        .first()
    )
    if not request:
        raise HTTPException(status_code=404, detail="Request not found.")
    if request.requested_by != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your request.")
    if request.status != UnenrollRequestStatusEnum.pending:
        raise HTTPException(status_code=409, detail="Request already resolved.")

    request.status = UnenrollRequestStatusEnum.cancelled
    request.updated_at = datetime.now(timezone.utc)
    db.commit()

    return MessageResponse(message="Removal request cancelled.")
