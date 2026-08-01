from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from auth_utils import RefreshToken
from db.data_events import emit_data_event, resolve_admin_audience, resolve_admin_ids, resolve_section_audience
from db.pool import get_db
from dependencies import get_current_user, require_role
from grading import compute_section_grade_for_student
from image_utils import delete_avatar_image, save_avatar_image
from models.assignment_model import Assignment
from models.enrollment_model import Enrollment
from models.inventory_model import InventoryItem
from models.notification_model import NotificationTypeEnum
from models.quest_model import Quest
from models.section_model import Section, SectionStatusEnum
from models.shop_item_model import ShopItem, ShopItemTypeEnum
from models.submission_model import Submission, SubmissionStatusEnum
from models.user_model import User, RoleEnum
from notifications import notify
from schemas.user import (
    UserResponse,
    UserListResponse,
    StudentSectionGradeResponse,
    ReportCardResponse,
    ProfileUpdateRequest,
    ProfilePictureResponse,
    FeaturedBadgeUpdateRequest,
)
from sqlalchemy import or_


class RejectSignupRequest(BaseModel):
    reason: Optional[str] = None


class VerifyUserRequest(BaseModel):
    # Required to match the target's own requested role when that role is
    # "admin" — see verify_user for why.
    confirm_role: Optional[RoleEnum] = None

router = APIRouter(prefix="/users", tags=["users"])


# NOTE: the "/me" routes must be registered before "/{user_id}" — otherwise
# FastAPI tries to parse "me" as the int user_id and fails with a 422 before
# ever reaching these handlers.
@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.username is not None:
        username = body.username.strip()
        if not username:
            raise HTTPException(status_code=400, detail="Username cannot be empty.")
        if len(username) > 30:
            raise HTTPException(status_code=400, detail="Username must be 30 characters or fewer.")

        existing = db.query(User).filter(
            User.username == username,
            User.school_id == current_user.school_id,
            User.user_id != current_user.user_id,
            User.is_archived == False,
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Username already taken.")
        current_user.username = username

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/profile-picture", response_model=ProfilePictureResponse)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Content-type is client-supplied and easily spoofed — it's just a fast
    # rejection. save_avatar_image() does the real, authoritative check by
    # actually decoding the bytes as an image.
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are allowed.")

    raw_bytes = await file.read()
    new_url = save_avatar_image(raw_bytes)

    old_url = current_user.profile_picture_url
    current_user.profile_picture_url = new_url
    db.commit()

    if old_url:
        delete_avatar_image(old_url)

    return ProfilePictureResponse(profile_picture_url=new_url)


@router.delete("/me/profile-picture", response_model=ProfilePictureResponse)
def delete_profile_picture(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    old_url = current_user.profile_picture_url
    if not old_url:
        raise HTTPException(status_code=404, detail="No profile picture to remove.")

    current_user.profile_picture_url = None
    db.commit()
    delete_avatar_image(old_url)

    return ProfilePictureResponse(profile_picture_url=None)


@router.patch("/me/featured-badge", response_model=UserResponse)
def set_my_featured_badge(
    body: FeaturedBadgeUpdateRequest,
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db),
):
    if body.item_id is not None:
        item = db.query(ShopItem).filter(
            ShopItem.item_id == body.item_id,
            ShopItem.is_archived == False,
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Badge not found.")
        if item.item_type != ShopItemTypeEnum.badge:
            raise HTTPException(status_code=400, detail="Only badges can be featured.")

        owned = db.query(InventoryItem).filter(
            InventoryItem.student_id == current_user.user_id,
            InventoryItem.item_id == body.item_id,
        ).first()
        if not owned:
            raise HTTPException(status_code=403, detail="You don't own this badge.")

    current_user.featured_badge_item_id = body.item_id
    db.commit()
    db.refresh(current_user)
    return current_user


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


@router.get("/{user_id}/grades", response_model=List[StudentSectionGradeResponse])
def get_student_grades(
    user_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    student = db.query(User).filter(
        User.user_id == user_id,
        User.school_id == current_user.school_id,
        User.is_archived == False,
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="User not found.")
    if student.role != RoleEnum.student:
        raise HTTPException(status_code=400, detail="User is not a student.")

    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == user_id,
        Enrollment.is_archived == False,
    ).all()

    results = []
    for enrollment in enrollments:
        section = db.query(Section).filter(
            Section.section_id == enrollment.section_id,
            Section.is_archived == False,
        ).first()
        if not section:
            continue
        grade = compute_section_grade_for_student(db, section.section_id, user_id)
        results.append({
            "section_id": section.section_id,
            "class_name": section.class_.name,
            "period": section.period,
            "percentage": grade["percentage"],
            "letter_grade": grade["letter_grade"],
        })
    return results


@router.get("/{user_id}/report_card", response_model=ReportCardResponse)
def get_student_report_card(
    user_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    student = db.query(User).filter(
        User.user_id == user_id,
        User.school_id == current_user.school_id,
        User.is_archived == False,
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="User not found.")
    if student.role != RoleEnum.student:
        raise HTTPException(status_code=400, detail="User is not a student.")

    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == user_id,
        Enrollment.is_archived == False,
    ).all()

    sections_out = []
    for enrollment in enrollments:
        section = db.query(Section).filter(
            Section.section_id == enrollment.section_id,
            Section.is_archived == False,
        ).first()
        if not section:
            continue

        grade = compute_section_grade_for_student(db, section.section_id, user_id)

        assignments = db.query(Assignment).filter(
            Assignment.section_id == section.section_id,
            Assignment.is_archived == False,
        ).all()
        submissions_by_assignment = {
            s.assignment_id: s
            for s in db.query(Submission).filter(
                Submission.student_id == user_id,
                Submission.assignment_id.in_([a.assignment_id for a in assignments]),
                Submission.is_archived == False,
            ).all()
        } if assignments else {}

        items = []
        for a in assignments:
            submission = submissions_by_assignment.get(a.assignment_id)
            items.append({
                "kind": "assignment",
                "item_id": a.assignment_id,
                "name": a.title,
                "category": a.category.value,
                "assigned_at": a.created_at,
                "grade": (
                    submission.grade
                    if submission and submission.status == SubmissionStatusEnum.graded and submission.grade is not None
                    else None
                ),
            })

        quests = db.query(Quest).filter(
            Quest.section_id == section.section_id,
            Quest.is_archived == False,
            or_(Quest.assigned_to.is_(None), Quest.assigned_to == user_id),
        ).all()
        for q in quests:
            items.append({
                "kind": "quest",
                "item_id": q.quest_id,
                "name": q.title,
                "category": q.category.value,
                "assigned_at": q.created_at,
                "grade": None,
            })

        items.sort(key=lambda i: i["assigned_at"])

        sections_out.append({
            "section_id": section.section_id,
            "class_name": section.class_.name,
            "period": section.period,
            "teacher_name": section.teacher.full_name if section.teacher else None,
            "percentage": grade["percentage"],
            "letter_grade": grade["letter_grade"],
            "items": items,
        })

    return {
        "student_id": student.user_id,
        "username": student.username,
        "full_name": student.full_name,
        "sections": sections_out,
    }


@router.patch("/{user_id}/verify")
def verify_user(
    user_id: int,
    body: Optional[VerifyUserRequest] = None,
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

    # A self-registered admin account is otherwise approved by the same
    # one-click flow as a student/teacher — this forces the approving admin
    # to explicitly echo back "admin" first, so a careless click can't grant
    # full admin rights to whoever requested them.
    if user.role == RoleEnum.admin and (not body or body.confirm_role != RoleEnum.admin):
        raise HTTPException(
            status_code=400,
            detail="Approving an admin signup requires confirming the requested role.",
        )

    user.is_verified = True
    emit_data_event(
        db, "users", "updated", current_user.school_id,
        resolve_admin_audience(db, current_user.school_id, [user_id]),
        ids={"user_id": user_id},
    )
    db.commit()
    return {"message": "User verified successfully."}


@router.patch("/{user_id}/reject")
def reject_signup(
    user_id: int,
    body: RejectSignupRequest,
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
    if user.is_verified:
        raise HTTPException(status_code=409, detail="User is already verified.")

    user.rejection_reason = body.reason or "Rejected by admin"
    emit_data_event(
        db, "users", "updated", current_user.school_id,
        resolve_admin_audience(db, current_user.school_id, [user_id]),
        ids={"user_id": user_id},
    )
    db.commit()
    return {"message": "Signup rejected."}


@router.patch("/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account.")

    user = db.query(User).filter(
        User.user_id == user_id,
        User.school_id == current_user.school_id,
        User.is_archived == False,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = False
    emit_data_event(
        db, "users", "updated", current_user.school_id,
        resolve_admin_audience(db, current_user.school_id, [user_id]),
        ids={"user_id": user_id},
    )
    db.commit()
    return {"message": "User deactivated successfully."}


@router.patch("/{user_id}/reactivate")
def reactivate_user(
    user_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.user_id == user_id,
        User.school_id == current_user.school_id,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = True
    emit_data_event(
        db, "users", "updated", current_user.school_id,
        resolve_admin_audience(db, current_user.school_id, [user_id]),
        ids={"user_id": user_id},
    )
    db.commit()
    return {"message": "User reactivated successfully."}


def _soft_delete_user(db: Session, user: User) -> None:
    """Archives a user and, for teachers, cascades the fallout onto their
    sections (pending_reassignment + notify enrolled students). Shared by
    the admin-on-others delete and the self-service delete below."""
    user.is_archived = True
    user.deleted_at = datetime.now(timezone.utc)

    if user.role == RoleEnum.teacher:
        sections = db.query(Section).filter(
            Section.teacher_id == user.user_id,
            Section.is_archived == False,
        ).all()
        for section in sections:
            section.status = SectionStatusEnum.pending_reassignment
            enrollments = db.query(Enrollment).filter(
                Enrollment.section_id == section.section_id,
                Enrollment.is_archived == False,
            ).all()
            notify(
                db,
                [enrollment.student_id for enrollment in enrollments],
                NotificationTypeEnum.section_status,
                f"Section #{section.section_id} is pending teacher reassignment.",
                entity_type="section",
                entity_id=section.section_id,
            )
            emit_data_event(
                db, "sections", "updated", section.school_id,
                resolve_section_audience(db, section),
                section_id=section.section_id,
            )


@router.delete("/me")
def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == RoleEnum.admin:
        other_admin = db.query(User).filter(
            User.school_id == current_user.school_id,
            User.role == RoleEnum.admin,
            User.is_archived == False,
            User.user_id != current_user.user_id,
        ).first()
        if not other_admin:
            raise HTTPException(
                status_code=409,
                detail="Cannot delete the last remaining admin at your school.",
            )

    _soft_delete_user(db, current_user)
    db.query(RefreshToken).filter(RefreshToken.user_id == current_user.user_id).delete()

    emit_data_event(
        db, "users", "deleted", current_user.school_id,
        resolve_admin_audience(db, current_user.school_id),
        ids={"user_id": current_user.user_id},
    )
    db.commit()
    return {"message": "Account deleted successfully."}


@router.post("/me/request-password-reset")
def request_password_reset(
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db),
):
    admin_ids = resolve_admin_ids(db, current_user.school_id)
    notify(
        db,
        admin_ids,
        NotificationTypeEnum.password_reset_requested,
        f"{current_user.full_name} ({current_user.username}) has requested a password reset.",
        entity_type="student",
        entity_id=current_user.user_id,
    )
    db.commit()
    return {"message": f"Notified {len(admin_ids)} admin(s)."}


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

    _soft_delete_user(db, user)

    emit_data_event(
        db, "users", "deleted", current_user.school_id,
        resolve_admin_audience(db, current_user.school_id),
        ids={"user_id": user_id},
    )
    db.commit()
    return {"message": "User deleted successfully."}
