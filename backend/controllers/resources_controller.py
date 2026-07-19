from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.pool import get_db
from dependencies import get_current_user, require_role
from models.enrollment_model import Enrollment
from models.resource_model import Resource
from models.section_model import Section
from models.user_model import User, RoleEnum
from schemas.resource import ResourceCreate, ResourceUpdate, ResourceResponse

router = APIRouter(tags=["resources"])


def _check_section_access(section_id: int, current_user: User, db: Session) -> Section:
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

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

    return section


def _get_owned_section(section_id: int, current_user: User, db: Session) -> Section:
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    if section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")
    return section


@router.get("/sections/{section_id}/resources", response_model=List[ResourceResponse])
def list_resources(
    section_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_section_access(section_id, current_user, db)
    return (
        db.query(Resource)
        .filter(Resource.section_id == section_id, Resource.is_archived == False)
        .order_by(Resource.created_at.desc())
        .all()
    )


@router.post("/sections/{section_id}/resources", response_model=ResourceResponse, status_code=201)
def create_resource(
    section_id: int,
    body: ResourceCreate,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    _get_owned_section(section_id, current_user, db)
    resource = Resource(
        section_id=section_id,
        teacher_id=current_user.user_id,
        title=body.title,
        url=body.url,
        description=body.description,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource
