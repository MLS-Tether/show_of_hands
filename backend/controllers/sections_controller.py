from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.pool import get_db
from dependencies import get_current_user, require_role
from models.enrollment_model import Enrollment, EnrollmentStatusEnum
from models.section_model import Section, SectionStatusEnum
from models.user_model import User, RoleEnum
from schemas.section import (
    SectionCreate,
    SectionUpdate,
    SectionListResponse,
    SectionResponse,
    SectionDetailResponse,
    SectionUpdateResponse,
)

router = APIRouter(prefix="/sections", tags=["sections"])


def _approved_enrollments(section_id: int, db: Session):
    return db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.status == EnrollmentStatusEnum.approved,
        Enrollment.is_archived == False,
    ).all()


def _build_list_item(section: Section, db: Session) -> dict:
    return {
        "section_id": section.section_id,
        "class_name": section.class_.name,
        "teacher_name": section.teacher.username if section.teacher else None,
        "period": section.period,
        "enrolled_count": len(_approved_enrollments(section.section_id, db)),
        "capacity": section.capacity,
        "status": section.status,
    }


def _build_detail(section: Section, db: Session) -> dict:
    approved = _approved_enrollments(section.section_id, db)
    assignments = [a for a in section.assignments if not a.is_archived]
    quests = [q for q in section.quests if not q.is_archived]
    return {
        "section_id": section.section_id,
        "class_name": section.class_.name,
        "teacher_name": section.teacher.username if section.teacher else None,
        "period": section.period,
        "capacity": section.capacity,
        "enrolled_count": len(approved),
        "status": section.status,
        "students": [
            {"user_id": e.student_id, "username": e.student.username}
            for e in approved
        ],
        "assignments": [
            {"assignment_id": a.assignment_id, "title": a.title, "due_date": a.due_date}
            for a in assignments
        ],
        "quests": [
            {"quest_id": q.quest_id, "title": q.title, "category": q.category}
            for q in quests
        ],
    }


@router.get("", response_model=List[SectionListResponse])
def list_sections(
    class_id: Optional[int] = None,
    current_user: User = Depends(require_role(["student", "teacher", "admin"])),
    db: Session = Depends(get_db),
):
    query = db.query(Section).filter(
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    )
    if class_id is not None:
        query = query.filter(Section.class_id == class_id)
    return [_build_list_item(s, db) for s in query.all()]


@router.post("", response_model=SectionResponse, status_code=201)
def create_section(
    body: SectionCreate,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    section = Section(
        class_id=body.class_id,
        school_id=current_user.school_id,
        teacher_id=current_user.user_id,
        period=body.period,
        capacity=body.capacity,
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return {
        "section_id": section.section_id,
        "class_name": section.class_.name,
        "period": section.period,
        "capacity": section.capacity,
        "status": section.status,
        "created_at": section.created_at,
    }


@router.get("/{section_id}", response_model=SectionDetailResponse)
def get_section(
    section_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    if section.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    if current_user.role == RoleEnum.student:
        enrolled = db.query(Enrollment).filter(
            Enrollment.section_id == section_id,
            Enrollment.student_id == current_user.user_id,
            Enrollment.status == EnrollmentStatusEnum.approved,
            Enrollment.is_archived == False,
        ).first()
        if not enrolled:
            raise HTTPException(status_code=403, detail="Not enrolled in this section.")
    elif current_user.role == RoleEnum.teacher:
        if section.teacher_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not your section.")

    return _build_detail(section, db)


@router.patch("/{section_id}", response_model=SectionUpdateResponse)
def update_section(
    section_id: int,
    body: SectionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (RoleEnum.teacher, RoleEnum.admin):
        raise HTTPException(status_code=403, detail="Unauthorized.")

    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    if current_user.role == RoleEnum.teacher:
        if section.teacher_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not your section.")
        if body.period is not None:
            section.period = body.period
        if body.capacity is not None:
            section.capacity = body.capacity
    else:
        if body.period is not None:
            section.period = body.period
        if body.capacity is not None:
            section.capacity = body.capacity
        if body.status is not None:
            section.status = body.status
        if body.teacher_id is not None:
            section.teacher_id = body.teacher_id

    db.commit()
    db.refresh(section)
    return section


@router.delete("/{section_id}")
def delete_section(
    section_id: int,
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

    section.is_archived = True
    section.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Section deleted successfully."}
