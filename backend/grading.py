from collections import defaultdict

from sqlalchemy.orm import Session

from models.assignment_model import Assignment
from models.submission_model import Submission, SubmissionStatusEnum

CATEGORY_WEIGHTS = {
    "homework": 0.30,
    "quizzes": 0.30,
    "tests": 0.40,
}


def letter_grade_for(percentage):
    """A=90-100, B=80-89, C=70-79, D=60-69, F=<60. No +/- modifiers."""
    if percentage is None:
        return None
    if percentage >= 90:
        return "A"
    if percentage >= 80:
        return "B"
    if percentage >= 70:
        return "C"
    if percentage >= 60:
        return "D"
    return "F"


def compute_cumulative_grade(graded_submissions_with_category):
    """
    graded_submissions_with_category: list of (grade, category) tuples for one
    student's graded submissions within one section.

    Groups by category, averages within each category, then computes a
    weighted average across categories present, renormalizing weights over
    only the categories that have at least one graded submission so a
    student isn't penalized for a category that hasn't started yet.
    """
    if not graded_submissions_with_category:
        return {"percentage": None, "letter_grade": None}

    grades_by_category = defaultdict(list)
    for grade, category in graded_submissions_with_category:
        grades_by_category[category].append(grade)

    category_averages = {
        category: sum(grades) / len(grades)
        for category, grades in grades_by_category.items()
    }

    present_weights = {
        category: CATEGORY_WEIGHTS[category]
        for category in category_averages
        if category in CATEGORY_WEIGHTS
    }
    total_weight = sum(present_weights.values())
    if total_weight == 0:
        return {"percentage": None, "letter_grade": None}

    percentage = sum(
        category_averages[category] * (weight / total_weight)
        for category, weight in present_weights.items()
    )

    return {"percentage": percentage, "letter_grade": letter_grade_for(percentage)}


def compute_section_grade_for_student(db: Session, section_id: int, student_id: int):
    submissions = (
        db.query(Submission.grade, Assignment.category)
        .join(Assignment, Submission.assignment_id == Assignment.assignment_id)
        .filter(
            Assignment.section_id == section_id,
            Assignment.is_archived == False,
            Submission.student_id == student_id,
            Submission.status == SubmissionStatusEnum.graded,
            Submission.grade.isnot(None),
            Submission.is_archived.is_(False),
        )
        .all()
    )

    graded = [(grade, category.value if hasattr(category, "value") else category) for grade, category in submissions]
    return compute_cumulative_grade(graded)
