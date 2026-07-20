from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.data_events import emit_data_event, resolve_admin_audience, resolve_section_audience
from db.pool import get_db
from dependencies import require_role
from models.enrollment_model import Enrollment
from models.point_transaction_model import PointTransaction, TransactionSourceEnum
from models.quest_completion_model import QuestCompletion
from models.quest_model import Quest
from models.section_model import Section
from models.user_model import User
from schemas.quest_completion import QuestCompletionResponse

router = APIRouter(prefix="/quests", tags=["quest-completions"])


@router.post("/{quest_id}/complete", response_model=QuestCompletionResponse, status_code=201)
def complete_quest(
    quest_id: int,
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

    completion = QuestCompletion(
        quest_id=quest_id,
        student_id=current_user.user_id,
        points_awarded=quest.point_value,
    )
    db.add(completion)
    db.flush()

    db.add(PointTransaction(
        user_id=current_user.user_id,
        amount=quest.point_value,
        source=TransactionSourceEnum.quest,
        source_id=quest_id,
    ))
    current_user.total_points += quest.point_value

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
