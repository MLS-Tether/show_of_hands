import os
from datetime import datetime, timezone, timedelta

from db.pool import SessionLocal
from auth_utils import hash_password
from models.class__model import Class_
from models.school_model import School
from models.user_model import User, RoleEnum
from models.section_model import Section, SectionStatusEnum
from models.enrollment_model import Enrollment
from models.assignment_model import Assignment
from models.submission_model import Submission, SubmissionStatusEnum
from models.quest_model import Quest, QuestCategoryEnum, QuestTypeEnum, QuestSourceEnum
from models.quest_completion_model import QuestCompletion
from models.help_request_model import HelpRequest
from models.notification_model import Notification, NotificationTypeEnum
from models.point_transaction_model import PointTransaction, TransactionSourceEnum

DEFAULT_CLASSES = [
    "Algebra",
    "Geometry",
    "Calculus",
    "Biology",
    "Chemistry",
    "Physics",
    "English Literature",
    "Creative Writing",
    "US History",
    "World History",
    "Economics",
    "Psychology",
    "Computer Science",
    "Art",
    "Music Theory",
    "Physical Education",
    "Spanish",
    "French",
    "Mandarin",
]

DEV_SCHOOL_CODE = "DEV001"
DEV_PASSWORD = "Passw0rd!"


def seed_classes():
    db = SessionLocal()
    try:
        if db.query(Class_).count() == 0:
            for name in DEFAULT_CLASSES:
                db.add(Class_(name=name))
            db.commit()
    finally:
        db.close()


def seed_dev_data():
    """Seeds a fixed demo school/roster/content set for local frontend dev and the demo.

    Gated on ENV=development so it never runs against a real deployment, and
    skipped entirely if the DEV001 school already exists so restarts don't
    duplicate it.
    """
    if os.getenv("ENV") != "development":
        return

    db = SessionLocal()
    try:
        if db.query(School).filter(School.school_code == DEV_SCHOOL_CODE).first():
            return

        now = datetime.now(timezone.utc)
        password_hash = hash_password(DEV_PASSWORD)

        school = School(name="Tether Demo School", school_code=DEV_SCHOOL_CODE)
        db.add(school)
        db.flush()

        def make_user(username: str, role: RoleEnum) -> User:
            user = User(
                school_id=school.school_id,
                username=username,
                password_hash=password_hash,
                role=role,
                is_verified=True,
            )
            db.add(user)
            db.flush()
            return user

        make_user("admin_demo", RoleEnum.admin)
        teacher = make_user("teacher_demo", RoleEnum.teacher)
        student_hero = make_user("student_hero", RoleEnum.student)
        student_chat = make_user("student_chat", RoleEnum.student)
        student_three = make_user("student_three", RoleEnum.student)
        student_four = make_user("student_four", RoleEnum.student)
        student_five = make_user("student_five", RoleEnum.student)

        cs_class = db.query(Class_).filter(Class_.name == "Computer Science").first()
        bio_class = db.query(Class_).filter(Class_.name == "Biology").first()
        if not cs_class or not bio_class:
            raise RuntimeError("seed_dev_data requires seed_classes() to have run first")

        section_a = Section(
            class_id=cs_class.class_id,
            school_id=school.school_id,
            teacher_id=teacher.user_id,
            period="3",
            capacity=30,
            status=SectionStatusEnum.active,
        )
        section_b = Section(
            class_id=bio_class.class_id,
            school_id=school.school_id,
            teacher_id=teacher.user_id,
            period="1",
            capacity=30,
            status=SectionStatusEnum.active,
        )
        db.add_all([section_a, section_b])
        db.flush()

        for student in (student_hero, student_chat, student_three):
            db.add(Enrollment(section_id=section_a.section_id, student_id=student.user_id))
        for student in (student_four, student_five):
            db.add(Enrollment(section_id=section_b.section_id, student_id=student.user_id))
        db.flush()

        # --- Section A assignments ---
        loops_quiz = Assignment(
            section_id=section_a.section_id,
            title="Intro to Loops Quiz",
            description="Covers for-loops, while-loops, and nested iteration.",
            due_date=now - timedelta(days=5),
            point_value=30,
        )
        binary_search_lab = Assignment(
            section_id=section_a.section_id,
            title="Binary Search Lab",
            description="Implement binary search and analyze its time complexity.",
            due_date=now + timedelta(days=4),
            point_value=40,
        )
        recursion_set = Assignment(
            section_id=section_a.section_id,
            title="Recursion Practice Set",
            description="A set of problems practicing recursive problem solving.",
            due_date=now + timedelta(days=7),
            point_value=50,
        )
        db.add_all([loops_quiz, binary_search_lab, recursion_set])

        # Section B: one assignment, for API/demo consistency only
        db.add(Assignment(
            section_id=section_b.section_id,
            title="Cell Structure Worksheet",
            description="Label and describe the parts of a eukaryotic cell.",
            due_date=now + timedelta(days=5),
            point_value=25,
        ))
        db.flush()

        # --- Pre-graded submission: student_hero already finished the Loops Quiz ---
        # Mirrors what create_submission()/finalize_submission() would have produced:
        # 25% on submit, then a grade->tier bonus on finalize (92 >= 85 -> 75% bonus).
        submitted_at = now - timedelta(days=6)
        finalized_at = now - timedelta(days=4)
        initial_points = int(loops_quiz.point_value * 0.25)
        bonus_points = int(loops_quiz.point_value * 0.75)

        db.add(Submission(
            assignment_id=loops_quiz.assignment_id,
            student_id=student_hero.user_id,
            content="Submitted via demo seed data.",
            status=SubmissionStatusEnum.graded,
            grade=92,
            points_awarded=initial_points + bonus_points,
            finalized_at=finalized_at,
            created_at=submitted_at,
            updated_at=finalized_at,
        ))
        db.add(PointTransaction(
            user_id=student_hero.user_id,
            amount=initial_points,
            source=TransactionSourceEnum.assignment,
            source_id=loops_quiz.assignment_id,
            awarded_at=submitted_at,
        ))
        db.add(PointTransaction(
            user_id=student_hero.user_id,
            amount=bonus_points,
            source=TransactionSourceEnum.assignment,
            source_id=loops_quiz.assignment_id,
            awarded_at=finalized_at,
        ))
        student_hero.total_points += initial_points + bonus_points

        # --- Section A quests ---
        attendance_quest = Quest(
            section_id=section_a.section_id,
            title="Perfect Attendance",
            description="Attend every class session this month.",
            category=QuestCategoryEnum.academic,
            point_value=15,
            quest_type=QuestTypeEnum.monthly,
            source=QuestSourceEnum.teacher,
        )
        reading_quest = Quest(
            section_id=section_a.section_id,
            title="Finish This Week's Reading",
            description="Complete the assigned reading before Friday.",
            category=QuestCategoryEnum.academic,
            point_value=20,
            quest_type=QuestTypeEnum.weekly,
            source=QuestSourceEnum.teacher,
        )
        social_quest = Quest(
            section_id=section_a.section_id,
            title="Help a Classmate",
            description="Help a classmate work through a problem this week.",
            category=QuestCategoryEnum.social,
            # Stored post-multiplier (10 base * 1.5), matching what create_quest() would persist.
            point_value=15,
            quest_type=QuestTypeEnum.weekly,
            source=QuestSourceEnum.teacher,
        )
        db.add_all([attendance_quest, reading_quest, social_quest])

        # Section B: one quest, for API/demo consistency only
        db.add(Quest(
            section_id=section_b.section_id,
            title="Lab Safety Refresher",
            description="Review the lab safety guidelines.",
            category=QuestCategoryEnum.academic,
            point_value=10,
            quest_type=QuestTypeEnum.weekly,
            source=QuestSourceEnum.teacher,
        ))
        db.flush()

        # --- Pre-completed quest: student_hero already finished Perfect Attendance ---
        completed_at = now - timedelta(days=2)
        db.add(QuestCompletion(
            quest_id=attendance_quest.quest_id,
            student_id=student_hero.user_id,
            points_awarded=attendance_quest.point_value,
            completed_at=completed_at,
        ))
        db.add(PointTransaction(
            user_id=student_hero.user_id,
            amount=attendance_quest.point_value,
            source=TransactionSourceEnum.quest,
            source_id=attendance_quest.quest_id,
            awarded_at=completed_at,
        ))
        student_hero.total_points += attendance_quest.point_value

        # --- Open help request: student_chat posts, student_hero accepts live in the demo ---
        db.add(HelpRequest(
            section_id=section_a.section_id,
            requester_id=student_chat.user_id,
            topic="Stuck on the recursion practice set",
            description="Can't figure out the base case for problem 3.",
            group_size=2,
            duration_minutes=30,
        ))

        # --- Notifications so student_hero's bell isn't empty on first login ---
        notification_specs = [
            (NotificationTypeEnum.enrollment_approved, "Your request to join Computer Science was approved."),
            (NotificationTypeEnum.new_assignment, f"New assignment posted: {loops_quiz.title}"),
            (NotificationTypeEnum.new_assignment, f"New assignment posted: {binary_search_lab.title}"),
            (NotificationTypeEnum.new_assignment, f"New assignment posted: {recursion_set.title}"),
            (NotificationTypeEnum.new_quest, f"New quest '{attendance_quest.title}' is available."),
            (NotificationTypeEnum.new_quest, f"New quest '{reading_quest.title}' is available."),
            (NotificationTypeEnum.new_quest, f"New quest '{social_quest.title}' is available."),
        ]
        for ntype, message in notification_specs:
            db.add(Notification(user_id=student_hero.user_id, type=ntype, message=message))

        db.commit()
    finally:
        db.close()
