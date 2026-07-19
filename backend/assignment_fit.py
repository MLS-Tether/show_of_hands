"""Deterministic class-performance snapshot used by the AI assignment-fit
advisor. All numbers shown to teachers come from here, never from the model."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from grading import compute_section_grade_for_student
from models.assignment_model import Assignment
from models.enrollment_model import Enrollment
from models.help_request_model import HelpRequest
from models.submission_model import Submission, SubmissionStatusEnum

RECENT_ASSIGNMENT_LIMIT = 10
HELP_REQUEST_WINDOW_DAYS = 60
HELP_REQUEST_TOPIC_LIMIT = 8


def build_section_snapshot(db: Session, section_id: int) -> dict:
    enrolled = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.is_archived == False,
    ).all()
    student_ids = [e.student_id for e in enrolled]

    graded = (
        db.query(Submission.grade, Assignment.category, Submission.assignment_id)
        .join(Assignment, Submission.assignment_id == Assignment.assignment_id)
        .filter(
            Assignment.section_id == section_id,
            Submission.status == SubmissionStatusEnum.graded,
            Submission.grade.isnot(None),
            Submission.is_archived == False,
            Assignment.is_archived == False,
        )
        .all()
    )

    grades_by_category = defaultdict(list)
    grades_by_assignment = defaultdict(list)
    for grade, category, assignment_id in graded:
        category_name = category.value if hasattr(category, "value") else category
        grades_by_category[category_name].append(grade)
        grades_by_assignment[assignment_id].append(grade)

    category_averages = {
        category: round(sum(grades) / len(grades), 1)
        for category, grades in grades_by_category.items()
    }

    distribution = Counter()
    for student_id in student_ids:
        result = compute_section_grade_for_student(db, section_id, student_id)
        letter = result["letter_grade"]
        if letter is not None:
            distribution[letter] += 1

    recent = (
        db.query(Assignment)
        .filter(Assignment.section_id == section_id, Assignment.is_archived == False)
        .order_by(Assignment.due_date.desc())
        .limit(RECENT_ASSIGNMENT_LIMIT)
        .all()
    )
    recent_assignments = []
    for assignment in recent:
        grades = grades_by_assignment.get(assignment.assignment_id, [])
        recent_assignments.append({
            "title": assignment.title,
            "category": assignment.category.value if hasattr(assignment.category, "value") else assignment.category,
            "class_average": round(sum(grades) / len(grades), 1) if grades else None,
            "graded_count": len(grades),
        })

    window_start = datetime.now(timezone.utc) - timedelta(days=HELP_REQUEST_WINDOW_DAYS)
    topic_rows = (
        db.query(HelpRequest.topic)
        .filter(
            HelpRequest.section_id == section_id,
            HelpRequest.is_archived == False,
            HelpRequest.created_at >= window_start,
        )
        .all()
    )
    topic_counts = Counter(row.topic for row in topic_rows)
    help_request_topics = [
        {"topic": topic, "count": count}
        for topic, count in topic_counts.most_common(HELP_REQUEST_TOPIC_LIMIT)
    ]

    return {
        "enrolled_count": len(student_ids),
        "graded_submission_count": len(graded),
        "category_averages": category_averages,
        "grade_distribution": dict(distribution),
        "recent_assignments": recent_assignments,
        "help_request_topics": help_request_topics,
    }
