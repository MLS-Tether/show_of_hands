from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session

from db.data_events import emit_data_event
from grading import compute_section_grade_for_student
from models.badge_rule_model import BadgeRule, BadgeRuleCriteriaEnum
from models.enrollment_model import Enrollment
from models.inventory_model import InventoryItem
from models.point_transaction_model import PointTransaction, TransactionSourceEnum
from models.quest_completion_model import QuestCompletion
from models.user_model import User


def evaluate_badges_for_student(db: Session, student_id: int, section_id: Optional[int] = None) -> None:
    """Runs every active badge rule against one student and awards any newly
    earned badges. Call right before the caller's own db.commit() — this only
    flushes, it never commits, so it stays inside the caller's transaction."""
    rules = db.query(BadgeRule).filter(BadgeRule.is_archived == False).all()
    for rule in rules:
        if _already_has(db, student_id, rule.item_id):
            continue
        if _EVALUATORS[rule.criteria_type](db, student_id, rule, section_id):
            _award_badge(db, student_id, rule.item_id)


def _already_has(db: Session, student_id: int, item_id: int) -> bool:
    return db.query(InventoryItem).filter(
        InventoryItem.student_id == student_id,
        InventoryItem.item_id == item_id,
    ).first() is not None


def _award_badge(db: Session, student_id: int, item_id: int) -> None:
    db.add(InventoryItem(student_id=student_id, item_id=item_id, is_equipped=False))
    db.flush()

    student = db.query(User).filter(User.user_id == student_id).first()
    if student:
        emit_data_event(db, "inventory", "updated", student.school_id, [student_id])


def _eval_first_quest(db: Session, student_id: int, rule: BadgeRule, section_id: Optional[int]) -> bool:
    count = db.query(QuestCompletion).filter(QuestCompletion.student_id == student_id).count()
    return count >= rule.threshold


def _eval_quest_total_count(db: Session, student_id: int, rule: BadgeRule, section_id: Optional[int]) -> bool:
    count = db.query(QuestCompletion).filter(QuestCompletion.student_id == student_id).count()
    return count >= rule.threshold


def _eval_event_count(db: Session, student_id: int, rule: BadgeRule, section_id: Optional[int]) -> bool:
    source = TransactionSourceEnum((rule.params or {}).get("source"))
    count = db.query(PointTransaction).filter(
        PointTransaction.user_id == student_id,
        PointTransaction.source == source,
    ).count()
    return count >= rule.threshold


def _eval_lifetime_points(db: Session, student_id: int, rule: BadgeRule, section_id: Optional[int]) -> bool:
    student = db.query(User).filter(User.user_id == student_id).first()
    return student is not None and student.total_points >= rule.threshold


def _longest_quest_streak(db: Session, student_id: int) -> int:
    completions = db.query(QuestCompletion.completed_at).filter(
        QuestCompletion.student_id == student_id,
    ).all()
    distinct_days = sorted({c.date() for (c,) in completions})
    if not distinct_days:
        return 0

    longest_streak = 1
    current_streak = 1
    for prev_day, day in zip(distinct_days, distinct_days[1:]):
        if day - prev_day == timedelta(days=1):
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 1
    return longest_streak


def _eval_quest_streak(db: Session, student_id: int, rule: BadgeRule, section_id: Optional[int]) -> bool:
    return _longest_quest_streak(db, student_id) >= rule.threshold


def _student_section_ids(db: Session, student_id: int) -> list:
    return [
        e.section_id
        for e in db.query(Enrollment).filter(
            Enrollment.student_id == student_id,
            Enrollment.is_archived == False,
        ).all()
    ]


def _best_section_grade_percentage(db: Session, student_id: int, section_ids: Optional[list] = None) -> float:
    """Highest computed percentage grade across the given sections (or all of
    the student's enrollments if none given). 0 if no section has a grade
    yet, so this is safe to use directly as a progress-bar "current" value."""
    ids = section_ids if section_ids is not None else _student_section_ids(db, student_id)
    best = 0.0
    for sid in ids:
        grade = compute_section_grade_for_student(db, sid, student_id)
        if grade["percentage"] is not None and grade["percentage"] > best:
            best = grade["percentage"]
    return best


def _eval_section_grade_threshold(db: Session, student_id: int, rule: BadgeRule, section_id: Optional[int]) -> bool:
    section_ids = [section_id] if section_id is not None else None
    return _best_section_grade_percentage(db, student_id, section_ids) >= rule.threshold


_EVALUATORS = {
    BadgeRuleCriteriaEnum.first_quest: _eval_first_quest,
    BadgeRuleCriteriaEnum.quest_total_count: _eval_quest_total_count,
    BadgeRuleCriteriaEnum.event_count: _eval_event_count,
    BadgeRuleCriteriaEnum.lifetime_points: _eval_lifetime_points,
    BadgeRuleCriteriaEnum.quest_streak: _eval_quest_streak,
    BadgeRuleCriteriaEnum.section_grade_threshold: _eval_section_grade_threshold,
}


def get_badge_progress(db: Session, student_id: int, rule: BadgeRule) -> dict:
    """Returns {current, target, unit} for a badge rule, for a student-facing
    progress display -- same underlying queries as the evaluators above, just
    returning the raw count/percentage instead of a threshold comparison."""
    if rule.criteria_type in (BadgeRuleCriteriaEnum.first_quest, BadgeRuleCriteriaEnum.quest_total_count):
        current = db.query(QuestCompletion).filter(QuestCompletion.student_id == student_id).count()
        unit = "quests completed"
    elif rule.criteria_type == BadgeRuleCriteriaEnum.event_count:
        source = TransactionSourceEnum((rule.params or {}).get("source"))
        current = db.query(PointTransaction).filter(
            PointTransaction.user_id == student_id,
            PointTransaction.source == source,
        ).count()
        unit = "help sessions"
    elif rule.criteria_type == BadgeRuleCriteriaEnum.lifetime_points:
        student = db.query(User).filter(User.user_id == student_id).first()
        current = student.total_points if student else 0
        unit = "points"
    elif rule.criteria_type == BadgeRuleCriteriaEnum.quest_streak:
        current = _longest_quest_streak(db, student_id)
        unit = "day streak"
    elif rule.criteria_type == BadgeRuleCriteriaEnum.section_grade_threshold:
        current = _best_section_grade_percentage(db, student_id)
        unit = "% grade in a section"
    else:
        current = 0
        unit = ""

    return {"current": current, "target": rule.threshold, "unit": unit}
