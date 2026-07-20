from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth_utils import hash_password, create_access_token, create_refresh_token
from db.data_events import emit_data_event
from db.pool import get_db
from dependencies import require_role
from models.school_model import School
from models.user_model import User, RoleEnum
from schemas.school import (
    SchoolResponse,
    SchoolCodeResponse,
    SchoolCreate,
    SchoolCreateResponse,
    SchoolUpdate,
    SchoolPointsResponse,
)

router = APIRouter(prefix="/schools", tags=["schools"])


def _generate_school_code(db: Session) -> str:
    for _ in range(5):
        code = uuid4().hex[:8].upper()
        exists = db.query(School).filter(School.school_code == code).first()
        if not exists:
            return code
    raise HTTPException(status_code=500, detail="Could not generate a unique school code.")


@router.post("", response_model=SchoolCreateResponse, status_code=201)
def create_school(body: SchoolCreate, db: Session = Depends(get_db)):
    existing_school = (
        db.query(School)
        .filter(School.name.ilike(body.school_name))
        .first()
    )
    if existing_school:
        raise HTTPException(status_code=409, detail="School name already taken.")

    school_code = _generate_school_code(db)

    school = School(name=body.school_name, school_code=school_code)
    db.add(school)
    db.flush()

    # admin_username only needs to be unique within the new school; since the school
    # was just created, there are no existing users to collide with.
    admin = User(
        school_id=school.school_id,
        username=body.admin_username,
        full_name=body.admin_username,
        password_hash=hash_password(body.admin_password),
        email=body.admin_email,
        role=RoleEnum.admin,
        is_verified=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(school)
    db.refresh(admin)

    access_token = create_access_token(admin.user_id, admin.role.value, admin.school_id)
    refresh_token = create_refresh_token(admin.user_id, db)

    return SchoolCreateResponse(
        school_id=school.school_id,
        name=school.name,
        school_code=school.school_code,
        admin_user_id=admin.user_id,
        admin_username=admin.username,
        created_at=school.created_at,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.get("/code", response_model=SchoolCodeResponse)
def get_school_code(
    current_user: User = Depends(require_role(["admin"])),
):
    return SchoolCodeResponse(school_code=current_user.school.school_code)


@router.get("/me", response_model=SchoolResponse)
def get_my_school(
    current_user: User = Depends(require_role(["student", "teacher", "admin"])),
):
    return current_user.school


@router.patch("/me", response_model=SchoolResponse)
def update_my_school(
    body: SchoolUpdate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    school = db.query(School).filter(School.school_id == current_user.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found.")

    if body.name is not None:
        school.name = body.name
    if body.district is not None:
        school.district = body.district
    if body.grades is not None:
        school.grades = body.grades

    emit_data_event(
        db, "school", "updated", school.school_id, [], broadcast=True,
    )
    db.commit()
    db.refresh(school)
    return school


@router.get("/points", response_model=SchoolPointsResponse)
def get_school_points(
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    total = (
        db.query(func.sum(User.total_points))
        .filter(User.school_id == current_user.school_id, User.is_archived == False)
        .scalar()
    )
    return SchoolPointsResponse(total_points=total or 0)
