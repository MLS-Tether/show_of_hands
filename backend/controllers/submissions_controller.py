from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.pool import get_db
from dependencies import get_current_user, require_role
from models.assignment_model import Assignment
from models.enrollment_model import Enrollment
from models.point_transaction_model import PointTransaction, TransactionSourceEnum
from models.section_model import Section
from models.submission_model import Submission, SubmissionStatusEnum
from models.user_model import User, RoleEnum
from schemas.submission import (
    SubmissionCreate,
    SubmissionGradeUpdate,
    SubmissionCreateResponse,
    SubmissionListResponse,
    SubmissionResponse,
    SubmissionGradeResponse,
    SubmissionFinalizeResponse,
)

router = APIRouter(tags=["submissions"])


def _get_assignment_or_404(assignment_id: int, db: Session) -> Assignment:
    assignment = db.query(Assignment).filter(
        Assignment.assignment_id == assignment_id,
        Assignment.is_archived == False,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    return assignment


def _check_teacher_owns_section(section_id: int, current_user: User, db: Session) -> Section:
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


def _award_points(user: User, amount: int, source: TransactionSourceEnum, source_id: int, db: Session):
    if amount <= 0:
        return
    db.add(PointTransaction(
        user_id=user.user_id,
        amount=amount,
        source=source,
        source_id=source_id,
    ))
    user.total_points += amount


@router.post("/assignments/{assignment_id}/submissions", response_model=SubmissionCreateResponse, status_code=201)
def create_submission(
    assignment_id: int,
    body: SubmissionCreate,
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db),
):
    assignment = _get_assignment_or_404(assignment_id, db)

    enrolled = db.query(Enrollment).filter(
        Enrollment.section_id == assignment.section_id,
        Enrollment.student_id == current_user.user_id,
        Enrollment.is_archived == False,
    ).first()
    if not enrolled:
        raise HTTPException(status_code=403, detail="Not enrolled in this section.")

    existing = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.student_id == current_user.user_id,
        Submission.is_archived == False,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already submitted for this assignment.")

    initial_points = int(assignment.point_value * 0.25)
    submission = Submission(
        assignment_id=assignment_id,
        student_id=current_user.user_id,
        content=body.content,
        file_url=body.file_url,
        points_awarded=initial_points,
    )
    db.add(submission)
    db.flush()

    _award_points(current_user, initial_points, TransactionSourceEnum.assignment, assignment_id, db)

    db.commit()
    db.refresh(submission)
    return submission


@router.get("/assignments/{assignment_id}/submissions", response_model=List[SubmissionListResponse])
def list_submissions(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (RoleEnum.teacher, RoleEnum.admin):
        raise HTTPException(status_code=403, detail="Unauthorized.")

    assignment = _get_assignment_or_404(assignment_id, db)

    section = db.query(Section).filter(
        Section.section_id == assignment.section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    if current_user.role == RoleEnum.teacher and section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")

    submissions = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.is_archived == False,
    ).all()

    return [
        {
            "submission_id": s.submission_id,
            "student_id": s.student_id,
            "username": s.student.username,
            "status": s.status,
            "grade": s.grade,
            "points_awarded": s.points_awarded,
            "created_at": s.created_at,
        }
        for s in submissions
    ]


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
def get_submission(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    submission = db.query(Submission).filter(
        Submission.submission_id == submission_id,
        Submission.is_archived == False,
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")

    assignment = submission.assignment
    section = db.query(Section).filter(
        Section.section_id == assignment.section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=403, detail="Access denied.")

    if current_user.role == RoleEnum.student:
        if submission.student_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not your submission.")
    elif current_user.role == RoleEnum.teacher:
        if section.teacher_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not your section.")

    return submission


@router.patch("/submissions/{submission_id}/grade", response_model=SubmissionGradeResponse)
def grade_submission(
    submission_id: int,
    body: SubmissionGradeUpdate,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    submission = db.query(Submission).filter(
        Submission.submission_id == submission_id,
        Submission.is_archived == False,
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if submission.status == SubmissionStatusEnum.graded:
        raise HTTPException(status_code=409, detail="Submission already finalized.")

    _check_teacher_owns_section(submission.assignment.section_id, current_user, db)

    submission.grade = body.grade
    submission.status = SubmissionStatusEnum.pending
    db.commit()
    db.refresh(submission)
    return submission


@router.post("/submissions/{submission_id}/finalize", response_model=SubmissionFinalizeResponse)
def finalize_submission(
    submission_id: int,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    submission = db.query(Submission).filter(
        Submission.submission_id == submission_id,
        Submission.is_archived == False,
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if submission.status == SubmissionStatusEnum.graded:
        raise HTTPException(status_code=409, detail="Submission already finalized.")

    _check_teacher_owns_section(submission.assignment.section_id, current_user, db)

    if submission.grade is None:
        raise HTTPException(status_code=400, detail="Cannot finalize without a grade.")

    point_value = submission.assignment.point_value
    grade = submission.grade

    if grade >= 85:
        additional = int(point_value * 0.75)
    elif grade >= 70:
        additional = int(point_value * 0.50)
    else:
        additional = 0

    student = db.query(User).filter(User.user_id == submission.student_id).first()
    _award_points(student, additional, TransactionSourceEnum.assignment, submission.assignment_id, db)

    submission.points_awarded += additional
    submission.status = SubmissionStatusEnum.graded
    submission.finalized_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(submission)
    return submission
