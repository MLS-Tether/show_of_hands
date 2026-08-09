import statistics
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from db.data_events import emit_data_event, resolve_admin_audience, resolve_section_audience
from db.pool import get_db
from dependencies import get_current_user, require_role
from grading import compute_section_grade_for_student
from models.assignment_model import Assignment
from models.enrollment_model import Enrollment
from models.help_request_model import HelpRequest
from models.section_model import Section, SectionStatusEnum
from models.study_room_model import StudyRoom, RoomMember
from models.submission_model import Submission, SubmissionStatusEnum
from models.user_model import User, RoleEnum
from schemas.section import (
    SectionCreate,
    SectionUpdate,
    SectionListResponse,
    SectionResponse,
    SectionDetailResponse,
    SectionUpdateResponse,
    SectionAnalyticsResponse,
    StudentGradeResponse,
    StudentGradeDetailResponse,
)

LOW_GRADE_THRESHOLD = 70

router = APIRouter(prefix="/sections", tags=["sections"])


def _build_list_item(section: Section, enrolled_count: int) -> dict:
    return {
        "section_id": section.section_id,
        "class_name": section.class_.name,
        "teacher_id": section.teacher_id,
        "teacher_name": section.teacher.username if section.teacher else None,
        "period": section.period,
        "enrolled_count": enrolled_count,
        "capacity": section.capacity,
        "status": section.status,
    }


def _build_detail(section: Section) -> dict:
    approved = [e for e in section.enrollments if not e.is_archived and not e.student.is_archived]
    assignments = [a for a in section.assignments if not a.is_archived]
    quests = [q for q in section.quests if not q.is_archived]
    return {
        "section_id": section.section_id,
        "class_name": section.class_.name,
        "teacher_name": section.teacher.username if section.teacher else None,
        "period": section.period,
        "capacity": section.capacity,
        "enrolled_count": len(approved),
        "status": section.status,
        "created_at": section.created_at,
        "students": [
            {"user_id": e.student_id, "username": e.student.username}
            for e in approved
        ],
        "assignments": [
            {"assignment_id": a.assignment_id, "title": a.title, "due_date": a.due_date}
            for a in assignments
        ],
        "quests": [
            {"quest_id": q.quest_id, "title": q.title, "category": q.category}
            for q in quests
        ],
    }


@router.get("", response_model=List[SectionListResponse])
def list_sections(
    class_id: Optional[int] = None,
    scope: str = "mine",
    current_user: User = Depends(require_role(["student", "teacher", "admin"])),
    db: Session = Depends(get_db),
):
    if scope not in ("mine", "all"):
        raise HTTPException(status_code=400, detail="Invalid scope. Must be 'mine' or 'all'.")

    query = db.query(Section).options(
        joinedload(Section.class_),
        joinedload(Section.teacher),
    ).filter(
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    )
    if class_id is not None:
        query = query.filter(Section.class_id == class_id)

    if current_user.role == RoleEnum.student and scope == "mine":
        enrolled_section_ids = {
            e.section_id
            for e in db.query(Enrollment).filter(
                Enrollment.student_id == current_user.user_id,
                Enrollment.is_archived == False,
            ).all()
        }
        query = query.filter(Section.section_id.in_(enrolled_section_ids))

    sections = query.all()

    # One grouped query for all enrolled-counts instead of one query per
    # section — this and the joinedload above are what turn this endpoint
    # from O(N) round-trips into a fixed 2, regardless of section count.
    counts = {}
    if sections:
        counts = dict(
            db.query(Enrollment.section_id, func.count(Enrollment.enrollment_id))
            .join(User, User.user_id == Enrollment.student_id)
            .filter(
                Enrollment.section_id.in_([s.section_id for s in sections]),
                Enrollment.is_archived == False,
                User.is_archived == False,
            )
            .group_by(Enrollment.section_id)
            .all()
        )

    return [_build_list_item(s, counts.get(s.section_id, 0)) for s in sections]


@router.post("", response_model=SectionResponse, status_code=201)
def create_section(
    body: SectionCreate,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    section = Section(
        class_id=body.class_id,
        school_id=current_user.school_id,
        teacher_id=current_user.user_id,
        period=body.period,
        capacity=body.capacity,
    )
    db.add(section)
    emit_data_event(
        db, "sections", "created", current_user.school_id,
        resolve_admin_audience(db, current_user.school_id, [current_user.user_id]),
    )
    db.commit()
    db.refresh(section)
    return {
        "section_id": section.section_id,
        "class_name": section.class_.name,
        "period": section.period,
        "capacity": section.capacity,
        "status": section.status,
        "created_at": section.created_at,
    }


@router.get("/{section_id}", response_model=SectionDetailResponse)
def get_section(
    section_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    section = db.query(Section).options(
        joinedload(Section.class_),
        joinedload(Section.teacher),
        selectinload(Section.enrollments),
        selectinload(Section.assignments),
        selectinload(Section.quests),
    ).filter(
        Section.section_id == section_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    if section.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Access denied.")

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

    return _build_detail(section)


@router.get("/{section_id}/analytics", response_model=SectionAnalyticsResponse)
def get_section_analytics(
    section_id: int,
    attention_page: int = 1,
    attention_page_size: int = 50,
    rooms_page: int = 1,
    rooms_page_size: int = 20,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: Session = Depends(get_db),
):
    if attention_page < 1:
        raise HTTPException(status_code=400, detail="attention_page must be 1 or greater.")
    if attention_page_size < 1:
        raise HTTPException(status_code=400, detail="attention_page_size must be 1 or greater.")
    if rooms_page < 1:
        raise HTTPException(status_code=400, detail="rooms_page must be 1 or greater.")
    if rooms_page_size < 1:
        raise HTTPException(status_code=400, detail="rooms_page_size must be 1 or greater.")
    section = db.query(Section).options(
        selectinload(Section.enrollments),
        selectinload(Section.assignments).selectinload(Assignment.submissions).joinedload(Submission.student),
    ).filter(
        Section.section_id == section_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    if section.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if current_user.role == RoleEnum.teacher and section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")

    approved_enrollments = [e for e in section.enrollments if not e.is_archived and not e.student.is_archived]
    approved_student_ids = {e.student_id for e in approved_enrollments}
    enrolled_count = len(approved_enrollments)
    assignments = [a for a in section.assignments if not a.is_archived]

    now = datetime.now(timezone.utc)
    per_student_points = {}
    assignment_analytics = []
    attention_by_student = {}

    def _flag_student(user_id, username, issue):
        entry = attention_by_student.setdefault(user_id, {"user_id": user_id, "username": username, "issues": []})
        entry["issues"].append(issue)

    for assignment in assignments:
        # Scoped to currently-approved enrollments -- a student removed from
        # the section afterward shouldn't keep inflating completion_rate
        # past 100%, or keep showing up flagged for a low grade below.
        submissions = [
            s for s in assignment.submissions
            if not s.is_archived and s.student_id in approved_student_ids
        ]
        graded = [s for s in submissions if s.status == SubmissionStatusEnum.graded]
        graded_grades = [s.grade for s in graded if s.grade is not None]

        for s in submissions:
            per_student_points[s.student_id] = per_student_points.get(s.student_id, 0) + s.points_awarded

        assignment_analytics.append({
            "assignment_id": assignment.assignment_id,
            "title": assignment.title,
            "point_value": assignment.point_value,
            "submitted_count": len(submissions),
            "graded_count": len(graded),
            "average_grade": statistics.mean(graded_grades) if graded_grades else None,
            "completion_rate": (len(submissions) / enrolled_count) if enrolled_count else 0.0,
        })

        for s in graded:
            if s.grade is not None and s.grade < LOW_GRADE_THRESHOLD:
                _flag_student(s.student_id, s.student.username, {
                    "reason": "low_grade",
                    "assignment_id": assignment.assignment_id,
                    "assignment_title": assignment.title,
                    "grade": s.grade,
                })

        if assignment.due_date < now:
            submitted_student_ids = {s.student_id for s in submissions}
            for enrollment in approved_enrollments:
                if enrollment.student_id not in submitted_student_ids:
                    _flag_student(enrollment.student_id, enrollment.student.username, {
                        "reason": "no_submission",
                        "assignment_id": assignment.assignment_id,
                        "assignment_title": assignment.title,
                    })

    all_flagged_students = sorted(attention_by_student.values(), key=lambda s: s["username"])
    attention_total_students = len(all_flagged_students)
    attention_total_pages = max(1, (attention_total_students + attention_page_size - 1) // attention_page_size)
    start = (attention_page - 1) * attention_page_size
    students_needing_attention = all_flagged_students[start:start + attention_page_size]

    points_totals = list(per_student_points.values())
    points_distribution = {
        "min": min(points_totals) if points_totals else None,
        "max": max(points_totals) if points_totals else None,
        "median": statistics.median(points_totals) if points_totals else None,
    }

    # The section-wide average is the mean of each student's own official
    # grade (grading.py's category-weighted formula, same one shown on their
    # individual grade page) rather than a flat mean of every raw submission
    # grade -- a flat mean ignores category weighting and missing overdue
    # work entirely, so it doesn't agree with the grades shown anywhere else.
    student_percentages = [
        compute_section_grade_for_student(db, section_id, student_id)["percentage"]
        for student_id in approved_student_ids
    ]
    student_percentages = [p for p in student_percentages if p is not None]

    all_rooms = (
        db.query(StudyRoom)
        .join(HelpRequest, StudyRoom.help_request_id == HelpRequest.help_request_id)
        .filter(HelpRequest.section_id == section_id)
        .options(
            joinedload(StudyRoom.help_request).joinedload(HelpRequest.requester),
            selectinload(StudyRoom.members).joinedload(RoomMember.user),
        )
        .order_by(StudyRoom.created_at.desc())
        .all()
    )
    study_rooms_total_rooms = len(all_rooms)
    study_rooms_total_pages = max(1, (study_rooms_total_rooms + rooms_page_size - 1) // rooms_page_size)
    rooms_start = (rooms_page - 1) * rooms_page_size
    page_rooms = all_rooms[rooms_start:rooms_start + rooms_page_size]
    study_rooms = [
        {
            "room_id": room.room_id,
            "help_request_id": room.help_request_id,
            "topic": room.help_request.topic,
            "requester_id": room.help_request.requester_id,
            "requester_username": room.help_request.requester.username,
            "status": room.status,
            "created_at": room.created_at,
            "members": [
                {"user_id": m.user_id, "username": m.user.username, "joined_at": m.joined_at}
                for m in sorted(room.members, key=lambda m: m.joined_at)
            ],
        }
        for room in page_rooms
    ]

    return {
        "section_id": section.section_id,
        "enrolled_count": enrolled_count,
        "assignment_count": len(assignments),
        "average_grade": statistics.mean(student_percentages) if student_percentages else None,
        "assignments": assignment_analytics,
        "points_distribution": points_distribution,
        "students_needing_attention": students_needing_attention,
        "attention_page": attention_page,
        "attention_page_size": attention_page_size,
        "attention_total_students": attention_total_students,
        "attention_total_pages": attention_total_pages,
        "study_rooms": study_rooms,
        "study_rooms_page": rooms_page,
        "study_rooms_page_size": rooms_page_size,
        "study_rooms_total_rooms": study_rooms_total_rooms,
        "study_rooms_total_pages": study_rooms_total_pages,
    }


def _get_section_for_grade_check(section_id: int, db: Session) -> Section:
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    return section


@router.get("/{section_id}/grades/me", response_model=StudentGradeResponse)
def get_my_section_grade(
    section_id: int,
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db),
):
    section = _get_section_for_grade_check(section_id, db)
    if section.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    enrolled = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.student_id == current_user.user_id,
        Enrollment.is_archived == False,
    ).first()
    if not enrolled:
        raise HTTPException(status_code=403, detail="Not enrolled in this section.")

    return compute_section_grade_for_student(db, section_id, current_user.user_id)


@router.get("/{section_id}/grades/{student_id}", response_model=StudentGradeResponse)
def get_student_section_grade(
    section_id: int,
    student_id: int,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: Session = Depends(get_db),
):
    section = _get_section_for_grade_check(section_id, db)
    if section.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if current_user.role == RoleEnum.teacher and section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")

    enrolled = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.student_id == student_id,
        Enrollment.is_archived == False,
    ).first()
    if not enrolled:
        raise HTTPException(status_code=404, detail="Student is not enrolled in this section.")

    return compute_section_grade_for_student(db, section_id, student_id)


@router.get("/{section_id}/grades/{student_id}/detail", response_model=StudentGradeDetailResponse)
def get_student_section_grade_detail(
    section_id: int,
    student_id: int,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: Session = Depends(get_db),
):
    section = _get_section_for_grade_check(section_id, db)
    if section.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if current_user.role == RoleEnum.teacher and section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")

    enrolled = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.student_id == student_id,
        Enrollment.is_archived == False,
    ).first()
    if not enrolled:
        raise HTTPException(status_code=404, detail="Student is not enrolled in this section.")

    grade = compute_section_grade_for_student(db, section_id, student_id)

    assignments = db.query(Assignment).filter(
        Assignment.section_id == section_id,
        Assignment.is_archived == False,
    ).order_by(Assignment.due_date).all()
    submissions_by_assignment = {
        s.assignment_id: s
        for s in db.query(Submission).filter(
            Submission.student_id == student_id,
            Submission.assignment_id.in_([a.assignment_id for a in assignments]),
            Submission.is_archived == False,
        ).all()
    } if assignments else {}

    assignment_items = []
    for a in assignments:
        submission = submissions_by_assignment.get(a.assignment_id)
        if submission is None:
            status, item_grade = "not_submitted", None
        else:
            status = submission.status.value
            item_grade = submission.grade if submission.status == SubmissionStatusEnum.graded else None
        assignment_items.append({
            "assignment_id": a.assignment_id,
            "title": a.title,
            "category": a.category.value,
            "due_date": a.due_date,
            "point_value": a.point_value,
            "status": status,
            "grade": item_grade,
            "submitted_at": submission.created_at if submission else None,
        })

    rooms = (
        db.query(StudyRoom)
        .join(HelpRequest, StudyRoom.help_request_id == HelpRequest.help_request_id)
        .filter(HelpRequest.section_id == section_id, HelpRequest.requester_id == student_id)
        .options(
            joinedload(StudyRoom.help_request),
            selectinload(StudyRoom.members).joinedload(RoomMember.user),
        )
        .order_by(StudyRoom.created_at.desc())
        .all()
    )
    study_rooms = [
        {
            "room_id": room.room_id,
            "help_request_id": room.help_request_id,
            "topic": room.help_request.topic,
            "status": room.status,
            "created_at": room.created_at,
            "members": [
                {"user_id": m.user_id, "username": m.user.username, "joined_at": m.joined_at}
                for m in sorted(room.members, key=lambda m: m.joined_at)
            ],
        }
        for room in rooms
    ]

    return {
        "percentage": grade["percentage"],
        "letter_grade": grade["letter_grade"],
        "assignments": assignment_items,
        "study_rooms": study_rooms,
    }


@router.patch("/{section_id}", response_model=SectionUpdateResponse)
def update_section(
    section_id: int,
    body: SectionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (RoleEnum.teacher, RoleEnum.admin):
        raise HTTPException(status_code=403, detail="Unauthorized.")

    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    if current_user.role == RoleEnum.teacher:
        if section.teacher_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not your section.")
        if body.period is not None:
            section.period = body.period
        if body.capacity is not None:
            section.capacity = body.capacity
    else:
        if body.period is not None:
            section.period = body.period
        if body.capacity is not None:
            section.capacity = body.capacity
        if body.status is not None:
            section.status = body.status
        if body.teacher_id is not None:
            new_teacher = db.query(User).filter(
                User.user_id == body.teacher_id,
                User.school_id == current_user.school_id,
                User.role == RoleEnum.teacher,
                User.is_archived == False,
            ).first()
            if not new_teacher:
                raise HTTPException(status_code=404, detail="Teacher not found.")
            section.teacher_id = body.teacher_id

    emit_data_event(
        db, "sections", "updated", section.school_id,
        resolve_section_audience(db, section),
        section_id=section_id,
    )
    db.commit()
    db.refresh(section)
    return section


@router.delete("/{section_id}")
def delete_section(
    section_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    section.is_archived = True
    section.deleted_at = datetime.now(timezone.utc)
    emit_data_event(
        db, "sections", "deleted", section.school_id,
        resolve_section_audience(db, section),
        section_id=section_id,
    )
    db.commit()
    return {"message": "Section deleted successfully."}
