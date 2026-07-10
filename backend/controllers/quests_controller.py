from datetime import datetime, timezone
from typing import List, Optional, Union, Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.pool import get_db
from dependencies import get_current_user, require_role
from models.enrollment_model import Enrollment
from models.notification_model import Notification, NotificationTypeEnum
from models.quest_completion_model import QuestCompletion
from models.quest_model import Quest, QuestCategoryEnum, QuestSourceEnum
from models.section_model import Section
from models.user_model import User, RoleEnum
from schemas.quest import QuestCreate, QuestResponse, QuestCreateResponse

router = APIRouter(tags=["quests"])


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


@router.get("/sections/{section_id}/quests", response_model=List[QuestResponse])
def list_quests(
    section_id: int,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_section_access(section_id, current_user, db)

    query = db.query(Quest).filter(
        Quest.section_id == section_id,
        Quest.is_archived == False,
    )
    if category is not None:
        try:
            category_enum = QuestCategoryEnum(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        query = query.filter(Quest.category == category_enum)

    quests = query.order_by(Quest.created_at.desc()).all()

    if current_user.role == RoleEnum.student:
        completed_quest_ids = {
            c.quest_id
            for c in db.query(QuestCompletion).filter(
                QuestCompletion.student_id == current_user.user_id,
                QuestCompletion.quest_id.in_([q.quest_id for q in quests]),
            ).all()
        }
        for quest in quests:
            quest.completed = quest.quest_id in completed_quest_ids

    return quests


@router.post("/sections/{section_id}/quests", response_model=QuestCreateResponse, status_code=201)
def create_quest(
    section_id: int,
    body: QuestCreate,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    if section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")

    assigned_to_id: Optional[int] = None if body.assigned_to == "all" else body.assigned_to

    if assigned_to_id is not None:
        from models.user_model import User as UserModel
        target_student = db.query(UserModel).filter(
            UserModel.user_id == assigned_to_id,
            UserModel.is_archived == False,
        ).first()
        if not target_student:
            raise HTTPException(status_code=404, detail="Target student not found.")

    point_value = int(body.point_value * 1.5) if body.category == QuestCategoryEnum.social else body.point_value

    quest = Quest(
        section_id=section_id,
        title=body.title,
        description=body.description,
        category=body.category,
        point_value=point_value,
        quest_type=body.quest_type,
        source=QuestSourceEnum.teacher,
        assigned_to=assigned_to_id,
    )
    db.add(quest)
    db.flush()

    if assigned_to_id is not None:
        notify_user_ids = [assigned_to_id]
    else:
        enrolled = db.query(Enrollment).filter(
            Enrollment.section_id == section_id,
            Enrollment.is_archived == False,
        ).all()
        notify_user_ids = [e.student_id for e in enrolled]

    for uid in notify_user_ids:
        db.add(Notification(
            user_id=uid,
            type=NotificationTypeEnum.new_quest,
            message=f"New quest '{quest.title}' is available.",
        ))

    db.commit()
    db.refresh(quest)
    return quest


@router.delete("/quests/{quest_id}")
def delete_quest(
    quest_id: int,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    quest = db.query(Quest).filter(
        Quest.quest_id == quest_id,
        Quest.is_archived == False,
    ).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found.")
    if quest.source == QuestSourceEnum.system:
        raise HTTPException(status_code=403, detail="Cannot delete system-generated quests.")

    section = db.query(Section).filter(
        Section.section_id == quest.section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section or section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your quest.")

    quest.is_archived = True
    quest.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Quest deleted successfully."}
