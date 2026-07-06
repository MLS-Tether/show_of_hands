from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.pool import get_db
from dependencies import get_current_user, require_role
from models.assignment_model import Assignment
from models.enrollment_model import Enrollment
from models.notification_model import Notification, NotificationTypeEnum
from models.section_model import Section
from models.user_model import User, RoleEnum
from schemas.assignment import (
    AssignmentCreate,
    AssignmentUpdate,
    AssignmentListResponse,
    AssignmentResponse,
    AssignmentUpdateResponse,
)

router = APIRouter(tags=["assignments"])


def _get_section_or_404(section_id: int, school_id: int, db: Session) -> Section:
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    return section


def _get_assignment_or_404(assignment_id: int, db: Session) -> Assignment:
    assignment = db.query(Assignment).filter(
        Assignment.assignment_id == assignment_id,
        Assignment.is_archived == False,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    return assignment


@router.get("/sections/{section_id}/assignments", response_model=List[AssignmentListResponse])
def list_assignments(
    section_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    section = _get_section_or_404(section_id, current_user.school_id, db)

    if current_user.role == RoleEnum.student:
        enrolled = db.query(Enrollment).filter(
            Enrollment.section_id == section_id,
            Enrollment.student_id == current_user.user_id,
            Enrollment.is_archived == False,
        ).first()
        if not enrolled:
            raise HTTPException(status_code=403, detail="Not enrolled in this section.")
    elif current_user.role == RoleEnum.teacher:
        if section.teacher_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not your section.")

    return db.query(Assignment).filter(
        Assignment.section_id == section_id,
        Assignment.is_archived == False,
    ).all()


@router.post("/sections/{section_id}/assignments", response_model=AssignmentResponse, status_code=201)
def create_assignment(
    section_id: int,
    body: AssignmentCreate,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    section = _get_section_or_404(section_id, current_user.school_id, db)
    if section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")

    assignment = Assignment(
        section_id=section_id,
        title=body.title,
        description=body.description,
        due_date=body.due_date,
        point_value=body.point_value,
    )
    db.add(assignment)
    db.flush()

    enrolled_students = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.is_archived == False,
    ).all()

    for enrollment in enrolled_students:
        db.add(Notification(
            user_id=enrollment.student_id,
            type=NotificationTypeEnum.new_assignment,
            message=f"New assignment posted: {body.title}",
        ))

    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/assignments/{assignment_id}", response_model=AssignmentResponse)
def get_assignment(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assignment = _get_assignment_or_404(assignment_id, db)
    section = _get_section_or_404(assignment.section_id, current_user.school_id, db)

    if current_user.role == RoleEnum.student:
        enrolled = db.query(Enrollment).filter(
            Enrollment.section_id == assignment.section_id,
            Enrollment.student_id == current_user.user_id,
            Enrollment.is_archived == False,
        ).first()
        if not enrolled:
            raise HTTPException(status_code=403, detail="Not enrolled in this section.")
    elif current_user.role == RoleEnum.teacher:
        if section.teacher_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not your section.")

    return assignment


@router.patch("/assignments/{assignment_id}", response_model=AssignmentUpdateResponse)
def update_assignment(
    assignment_id: int,
    body: AssignmentUpdate,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    assignment = _get_assignment_or_404(assignment_id, db)
    section = _get_section_or_404(assignment.section_id, current_user.school_id, db)

    if section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")

    if body.title is not None:
        assignment.title = body.title
    if body.description is not None:
        assignment.description = body.description
    if body.due_date is not None:
        assignment.due_date = body.due_date
    if body.point_value is not None:
        assignment.point_value = body.point_value

    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/assignments/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (RoleEnum.teacher, RoleEnum.admin):
        raise HTTPException(status_code=403, detail="Unauthorized.")

    assignment = _get_assignment_or_404(assignment_id, db)
    section = _get_section_or_404(assignment.section_id, current_user.school_id, db)

    if current_user.role == RoleEnum.teacher and section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")

    assignment.is_archived = True
    assignment.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Assignment deleted successfully."}
