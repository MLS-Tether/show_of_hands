from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.data_events import emit_data_event, resolve_admin_audience, resolve_section_audience
from db.pool import get_db
from dependencies import get_current_user, require_role
from models.enrollment_model import Enrollment
from models.point_transaction_model import PointTransaction, TransactionSourceEnum
from models.quest_completion_model import QuestCompletion
from models.quest_model import Quest
from models.section_model import Section
from models.user_model import User, RoleEnum
from quest_submission_utils import save_quest_submission_file
from schemas.quest_completion import QuestCompletionListResponse, QuestCompletionResponse
from services.badge_rules import evaluate_badges_for_student

router = APIRouter(prefix="/quests", tags=["quest-completions"])

MAX_DESCRIPTION_LENGTH = 500
ALLOWED_SUBMISSION_CONTENT_TYPES = ("image/jpeg", "application/pdf")


def _check_teacher_owns_quest_section(quest: Quest, current_user: User, db: Session) -> Section:
    section = db.query(Section).filter(
        Section.section_id == quest.section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    if current_user.role == RoleEnum.teacher and section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")
    return section


@router.post("/{quest_id}/complete", response_model=QuestCompletionResponse, status_code=201)
async def complete_quest(
    quest_id: int,
    description: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db),
):
    quest = db.query(Quest).filter(
        Quest.quest_id == quest_id,
        Quest.is_archived == False,
    ).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found.")

    section = db.query(Section).filter(
        Section.section_id == quest.section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=403, detail="Access denied.")

    enrolled = db.query(Enrollment).filter(
        Enrollment.section_id == quest.section_id,
        Enrollment.student_id == current_user.user_id,
        Enrollment.is_archived == False,
    ).first()
    if not enrolled:
        raise HTTPException(status_code=403, detail="Not enrolled in this section.")

    if quest.assigned_to is not None and quest.assigned_to != current_user.user_id:
        raise HTTPException(status_code=403, detail="This quest is not assigned to you.")

    already_completed = db.query(QuestCompletion).filter(
        QuestCompletion.quest_id == quest_id,
        QuestCompletion.student_id == current_user.user_id,
    ).first()
    if already_completed:
        raise HTTPException(status_code=409, detail="Quest already completed.")

    if description is not None:
        description = description.strip() or None
    if description is not None and len(description) > MAX_DESCRIPTION_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Description must be {MAX_DESCRIPTION_LENGTH} characters or fewer.",
        )

    file_url = None
    if file is not None:
        # Content-type is client-supplied and easily spoofed — it's just a fast
        # rejection. save_quest_submission_file() does the real, authoritative
        # check by actually inspecting the bytes.
        if file.content_type not in ALLOWED_SUBMISSION_CONTENT_TYPES:
            raise HTTPException(status_code=400, detail="Only JPEG images and PDFs are allowed.")
        raw_bytes = await file.read()
        file_url = save_quest_submission_file(raw_bytes, file.content_type)

    completion = QuestCompletion(
        quest_id=quest_id,
        student_id=current_user.user_id,
        points_awarded=quest.point_value,
        description=description,
        file_url=file_url,
    )
    db.add(completion)
    try:
        db.flush()
    except IntegrityError:
        # Two concurrent complete requests can both pass the `already_completed`
        # check above before either commits — the DB-level unique constraint on
        # (quest_id, student_id) is what actually prevents the double-award;
        # this just turns that into a clean 409 instead of a 500.
        db.rollback()
        raise HTTPException(status_code=409, detail="Quest already completed.")

    db.add(PointTransaction(
        user_id=current_user.user_id,
        amount=quest.point_value,
        source=TransactionSourceEnum.quest,
        source_id=quest_id,
    ))
    current_user.total_points += quest.point_value

    evaluate_badges_for_student(db, current_user.user_id, section_id=section.section_id)

    emit_data_event(
        db, "quests", "updated", section.school_id,
        resolve_section_audience(db, section),
        section_id=section.section_id, ids={"quest_id": quest_id},
    )
    emit_data_event(
        db, "points", "updated", section.school_id,
        resolve_admin_audience(db, section.school_id, [current_user.user_id]),
        ids={"user_id": current_user.user_id},
    )
    db.commit()
    db.refresh(completion)
    return completion


@router.get("/{quest_id}/completions", response_model=List[QuestCompletionListResponse])
def list_quest_completions(
    quest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (RoleEnum.teacher, RoleEnum.admin):
        raise HTTPException(status_code=403, detail="Unauthorized.")

    quest = db.query(Quest).filter(
        Quest.quest_id == quest_id,
        Quest.is_archived == False,
    ).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found.")

    _check_teacher_owns_quest_section(quest, current_user, db)

    completions = db.query(QuestCompletion).filter(QuestCompletion.quest_id == quest_id).all()

    return [
        {
            "quest_completion_id": c.quest_completion_id,
            "student_id": c.student_id,
            "username": c.student.username,
            "description": c.description,
            "file_url": c.file_url,
            "points_awarded": c.points_awarded,
            "completed_at": c.completed_at,
        }
        for c in completions
    ]
