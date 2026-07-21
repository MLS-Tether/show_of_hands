import os
import random
from datetime import datetime, timezone, timedelta

from db.pool import SessionLocal
from auth_utils import hash_password
from models.class__model import Class_
from models.school_model import School
from models.user_model import User, RoleEnum
from models.section_model import Section, SectionStatusEnum
from models.enrollment_model import Enrollment
from models.assignment_model import Assignment, AssignmentCategoryEnum
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
                full_name=username,
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
            category=AssignmentCategoryEnum.quizzes,
        )
        binary_search_lab = Assignment(
            section_id=section_a.section_id,
            title="Binary Search Lab",
            description="Implement binary search and analyze its time complexity.",
            due_date=now + timedelta(days=4),
            point_value=40,
            category=AssignmentCategoryEnum.homework,
        )
        recursion_set = Assignment(
            section_id=section_a.section_id,
            title="Recursion Practice Set",
            description="A set of problems practicing recursive problem solving.",
            due_date=now + timedelta(days=7),
            point_value=50,
            category=AssignmentCategoryEnum.tests,
        )
        db.add_all([loops_quiz, binary_search_lab, recursion_set])

        # Section B: one assignment, for API/demo consistency only
        cell_worksheet = Assignment(
            section_id=section_b.section_id,
            title="Cell Structure Worksheet",
            description="Label and describe the parts of a eukaryotic cell.",
            due_date=now + timedelta(days=5),
            point_value=25,
            category=AssignmentCategoryEnum.homework,
        )
        db.add(cell_worksheet)
        db.flush()

        def seed_graded_submission(assignment, student, grade, submitted_days_ago, finalized_days_ago):
            """Mirrors what create_submission()/finalize_submission() would have
            produced: 25% on submit, then a grade->tier bonus on finalize
            (grade >= 85 -> +75%, grade >= 70 -> +50%, else +0%)."""
            submitted_at = now - timedelta(days=submitted_days_ago)
            finalized_at = now - timedelta(days=finalized_days_ago)
            initial_points = int(assignment.point_value * 0.25)
            bonus_points = (
                int(assignment.point_value * 0.75) if grade >= 85
                else int(assignment.point_value * 0.50) if grade >= 70
                else 0
            )
            db.add(Submission(
                assignment_id=assignment.assignment_id,
                student_id=student.user_id,
                content="Submitted via demo seed data.",
                status=SubmissionStatusEnum.graded,
                grade=grade,
                points_awarded=initial_points + bonus_points,
                finalized_at=finalized_at,
                created_at=submitted_at,
                updated_at=finalized_at,
            ))
            db.add(PointTransaction(
                user_id=student.user_id,
                amount=initial_points,
                source=TransactionSourceEnum.assignment,
                source_id=assignment.assignment_id,
                awarded_at=submitted_at,
            ))
            db.add(PointTransaction(
                user_id=student.user_id,
                amount=bonus_points,
                source=TransactionSourceEnum.assignment,
                source_id=assignment.assignment_id,
                awarded_at=finalized_at,
            ))
            student.total_points += initial_points + bonus_points

        # --- Pre-graded submissions across all three categories, spread across
        # students so the cumulative-grade views land in different letter
        # bands: student_hero -> A, student_chat -> B, student_three -> D,
        # student_four -> C, student_five -> F.
        seed_graded_submission(loops_quiz, student_hero, 95, 6, 4)
        seed_graded_submission(binary_search_lab, student_hero, 92, 5, 3)
        seed_graded_submission(recursion_set, student_hero, 90, 2, 1)

        seed_graded_submission(loops_quiz, student_chat, 85, 6, 4)
        seed_graded_submission(binary_search_lab, student_chat, 87, 5, 3)
        seed_graded_submission(recursion_set, student_chat, 83, 2, 1)

        seed_graded_submission(loops_quiz, student_three, 65, 6, 4)
        seed_graded_submission(binary_search_lab, student_three, 68, 5, 3)
        seed_graded_submission(recursion_set, student_three, 60, 2, 1)

        seed_graded_submission(cell_worksheet, student_four, 75, 4, 2)
        seed_graded_submission(cell_worksheet, student_five, 50, 4, 2)

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


# Target weighted-average per student, spanning A/B/C/D/F evenly (3 each) so
# the section's grade distribution and category averages look like a real
# class roster rather than a handful of demo accounts.
CS_EXTRA_STUDENT_TARGETS = [96, 93, 90, 87, 84, 81, 78, 75, 72, 69, 64, 60, 55, 50, 44]


def seed_more_cs_students(count: int = 15):
    """Adds `count` more students to teacher_demo's existing Computer Science
    section (section_a from seed_dev_data()) with varying grades on its 3
    existing assignments, so the assignment-fit advisor has a realistic
    class size and grade spread to reason over instead of just 3 students.

    Guarded on the first new student's username already existing, so reruns
    (e.g. app restarts) don't duplicate the roster.
    """
    if os.getenv("ENV") != "development":
        return

    db = SessionLocal()
    try:
        school = db.query(School).filter(School.school_code == DEV_SCHOOL_CODE).first()
        if not school:
            return  # seed_dev_data() hasn't run yet -- nothing to attach to

        if db.query(User).filter(
            User.school_id == school.school_id,
            User.username == "cs_student_01",
        ).first():
            return

        cs_class = db.query(Class_).filter(Class_.name == "Computer Science").first()
        section = db.query(Section).filter(
            Section.school_id == school.school_id,
            Section.class_id == cs_class.class_id,
        ).first()
        if not cs_class or not section:
            raise RuntimeError("seed_more_cs_students requires seed_dev_data() to have run first")

        assignments = {
            a.title: a
            for a in db.query(Assignment).filter(Assignment.section_id == section.section_id).all()
        }
        loops_quiz = assignments["Intro to Loops Quiz"]
        binary_search_lab = assignments["Binary Search Lab"]
        recursion_set = assignments["Recursion Practice Set"]

        now = datetime.now(timezone.utc)
        password_hash = hash_password(DEV_PASSWORD)

        def seed_graded_submission(assignment, student, grade, submitted_days_ago, finalized_days_ago):
            """Same 25%-on-submit + grade-tier bonus formula as seed_dev_data()."""
            submitted_at = now - timedelta(days=submitted_days_ago)
            finalized_at = now - timedelta(days=finalized_days_ago)
            initial_points = int(assignment.point_value * 0.25)
            bonus_points = (
                int(assignment.point_value * 0.75) if grade >= 85
                else int(assignment.point_value * 0.50) if grade >= 70
                else 0
            )
            db.add(Submission(
                assignment_id=assignment.assignment_id,
                student_id=student.user_id,
                content="Submitted via demo seed data.",
                status=SubmissionStatusEnum.graded,
                grade=grade,
                points_awarded=initial_points + bonus_points,
                finalized_at=finalized_at,
                created_at=submitted_at,
                updated_at=finalized_at,
            ))
            db.add(PointTransaction(
                user_id=student.user_id,
                amount=initial_points,
                source=TransactionSourceEnum.assignment,
                source_id=assignment.assignment_id,
                awarded_at=submitted_at,
            ))
            db.add(PointTransaction(
                user_id=student.user_id,
                amount=bonus_points,
                source=TransactionSourceEnum.assignment,
                source_id=assignment.assignment_id,
                awarded_at=finalized_at,
            ))
            student.total_points += initial_points + bonus_points

        for i in range(1, count + 1):
            target = CS_EXTRA_STUDENT_TARGETS[(i - 1) % len(CS_EXTRA_STUDENT_TARGETS)]
            username = f"cs_student_{i:02d}"
            student = User(
                school_id=school.school_id,
                username=username,
                full_name=f"CS Student {i:02d}",
                password_hash=password_hash,
                role=RoleEnum.student,
                is_verified=True,
            )
            db.add(student)
            db.flush()

            db.add(Enrollment(section_id=section.section_id, student_id=student.user_id))

            def jittered(base, spread):
                return max(0, min(100, round(base + random.uniform(-spread, spread), 1)))

            quiz_grade = jittered(target, 4)
            hw_grade = jittered(target, 4)
            test_grade = jittered(target, 3)

            seed_graded_submission(loops_quiz, student, quiz_grade, 6, 4)
            seed_graded_submission(binary_search_lab, student, hw_grade, 5, 3)
            seed_graded_submission(recursion_set, student, test_grade, 2, 1)

        db.commit()
    finally:
        db.close()


def seed_second_teacher_data():
    """Adds a second teacher (teacher_demo2) with 3 sections of her own, each
    with 3 assignments, 3 quests, and a random subset of the existing seeded
    students enrolled.

    Runs independently of seed_dev_data()'s DEV001-existence short-circuit --
    guarded on teacher_demo2 already existing instead -- so it still
    populates an already-seeded database on the next restart rather than
    only ever applying to a brand-new one. teacher_demo is never referenced
    here; this is entirely teacher_demo2's own roster of sections.
    """
    if os.getenv("ENV") != "development":
        return

    db = SessionLocal()
    try:
        school = db.query(School).filter(School.school_code == DEV_SCHOOL_CODE).first()
        if not school:
            return  # seed_dev_data() hasn't run yet -- nothing to attach to

        if db.query(User).filter(
            User.school_id == school.school_id,
            User.username == "teacher_demo2",
        ).first():
            return

        now = datetime.now(timezone.utc)
        password_hash = hash_password(DEV_PASSWORD)

        def make_user(username: str, role: RoleEnum) -> User:
            user = User(
                school_id=school.school_id,
                username=username,
                full_name=username,
                password_hash=password_hash,
                role=role,
                is_verified=True,
            )
            db.add(user)
            db.flush()
            return user

        teacher = make_user("teacher_demo2", RoleEnum.teacher)

        existing_students = db.query(User).filter(
            User.school_id == school.school_id,
            User.role == RoleEnum.student,
        ).all()

        # Distinct from teacher_demo's classes (Computer Science, Biology).
        class_names = ["Chemistry", "Physics", "Economics"]
        classes = []
        for name in class_names:
            cls = db.query(Class_).filter(Class_.name == name).first()
            if not cls:
                raise RuntimeError(f"seed_second_teacher_data requires seed_classes() to have seeded '{name}'")
            classes.append(cls)

        sections = []
        for i, cls in enumerate(classes):
            section = Section(
                class_id=cls.class_id,
                school_id=school.school_id,
                teacher_id=teacher.user_id,
                period=str(i + 4),
                capacity=30,
                status=SectionStatusEnum.active,
            )
            db.add(section)
            sections.append(section)
        db.flush()

        for i, (section, cls) in enumerate(zip(sections, classes)):
            # Random subset per section so coverage varies but nobody's empty.
            sample_size = min(len(existing_students), random.randint(2, 5))
            for student in random.sample(existing_students, k=sample_size):
                db.add(Enrollment(section_id=section.section_id, student_id=student.user_id))

            categories_cycle = [
                AssignmentCategoryEnum.homework,
                AssignmentCategoryEnum.quizzes,
                AssignmentCategoryEnum.tests,
            ]
            for j in range(3):
                db.add(Assignment(
                    section_id=section.section_id,
                    title=f"{cls.name} Assignment {j + 1}",
                    description=f"Assignment {j + 1} for {cls.name}.",
                    due_date=now + timedelta(days=(j - 1) * 5),
                    point_value=20 + j * 10,
                    category=categories_cycle[j],
                ))

            quest_specs = [
                (QuestCategoryEnum.academic, QuestTypeEnum.daily, 10),
                (QuestCategoryEnum.academic, QuestTypeEnum.weekly, 20),
                # Stored post-multiplier (10 base * 1.5), matching what
                # create_quest() would persist for a social-category quest.
                (QuestCategoryEnum.social, QuestTypeEnum.weekly, 15),
            ]
            for k, (category, quest_type, point_value) in enumerate(quest_specs):
                db.add(Quest(
                    section_id=section.section_id,
                    title=f"{cls.name} Quest {k + 1}",
                    description=f"Quest {k + 1} for {cls.name}.",
                    category=category,
                    point_value=point_value,
                    quest_type=quest_type,
                    source=QuestSourceEnum.teacher,
                ))

        db.commit()
    finally:
        db.close()
