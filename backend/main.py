import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from apscheduler.schedulers.background import BackgroundScheduler

from db.pool import SessionLocal
from db.seed import (
    seed_classes,
    seed_dev_data,
    seed_second_teacher_data,
    seed_more_cs_students,
    seed_shop_items,
    seed_badge_rules,
)
from db.ws_broadcast import start_listener, stop_listener, deliver_loop
from models.assignment_model import Assignment
from models.enrollment_model import Enrollment
from models.submission_model import Submission, SubmissionStatusEnum
from models.notification_model import Notification, NotificationTypeEnum
from models.study_room_model import StudyRoom, StudyRoomStatusEnum
from models.help_request_model import HelpRequestStatusEnum
from notifications import notify

from controllers.auth_controller import router as auth_router
from controllers.schools_controller import router as schools_router
from controllers.classes_controller import router as classes_router
from controllers.class_requests_controller import router as class_requests_router
from controllers.sections_controller import router as sections_router
from controllers.enrollment_requests_controller import router as enrollment_requests_router
from controllers.unenroll_requests_controller import router as unenroll_requests_router
from controllers.assignments_controller import router as assignments_router
from controllers.submissions_controller import router as submissions_router
from controllers.quests_controller import router as quests_router
from controllers.quest_completions_controller import router as quest_completions_router
from controllers.points_controller import router as points_router
from controllers.help_requests_controller import router as help_requests_router
from controllers.rooms_controller import (
    router as rooms_router,
    room_registry,
    room_messages,
    _close_room_connections,
    _teardown_daily_room,
    _emit_room_events,
)
from controllers.notifications_controller import (
    router as notifications_router,
    deliver_notifications,
    deliver_data_events,
)
from controllers.users_controller import router as users_router
from controllers.resources_controller import router as resources_router
from controllers.assignment_fit_controller import router as assignment_fit_router
from controllers.shop_controller import router as shop_router

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()

# Set once the asyncio loop is running (see lifespan below) so the
# thread-based scheduler can hand async websocket teardown work back to it —
# BackgroundScheduler jobs run in their own worker threads, not on the loop.
_event_loop = None


def check_pending_grades():
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=10)
        stale_submissions = (
            db.query(Submission)
            .filter(Submission.status == SubmissionStatusEnum.pending)
            .filter(Submission.updated_at <= cutoff)
            .filter(Submission.reminder_sent_at.is_(None))
            .filter(Submission.is_archived == False)
            .all()
        )
        for submission in stale_submissions:
            section = submission.assignment.section
            if section.teacher_id is None:
                continue
            notify(
                db,
                section.teacher_id,
                NotificationTypeEnum.grade_finalization_reminder,
                (
                    f"Submission #{submission.submission_id} has been pending "
                    "grading for over 10 days."
                ),
                entity_type="section",
                entity_id=section.section_id,
            )
            submission.reminder_sent_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def check_overdue_assignments():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        overdue_assignments = (
            db.query(Assignment)
            .filter(Assignment.due_date < now)
            .filter(Assignment.is_archived == False)
            .all()
        )
        for assignment in overdue_assignments:
            enrolled = db.query(Enrollment).filter(
                Enrollment.section_id == assignment.section_id,
                Enrollment.is_archived == False,
            ).all()
            for enrollment in enrolled:
                submitted = db.query(Submission).filter(
                    Submission.assignment_id == assignment.assignment_id,
                    Submission.student_id == enrollment.student_id,
                    Submission.is_archived == False,
                ).first()
                if submitted:
                    continue

                already_notified = db.query(Notification).filter(
                    Notification.user_id == enrollment.student_id,
                    Notification.assignment_id == assignment.assignment_id,
                    Notification.type == NotificationTypeEnum.assignment_overdue,
                ).first()
                if already_notified:
                    continue

                notify(
                    db,
                    enrollment.student_id,
                    NotificationTypeEnum.assignment_overdue,
                    f"Assignment '{assignment.title}' is overdue.",
                    entity_type="assignment",
                    entity_id=assignment.assignment_id,
                    assignment_id=assignment.assignment_id,
                )
        db.commit()
    finally:
        db.close()


def check_expired_rooms():
    """A room whose countdown timer lapses is never auto-closed server-side —
    closing has always relied on an explicit /close, /leave, or /kick call.
    A requester who just closes the tab (or whose device dies) leaves the
    room 'active' in the DB forever, and its full chat history sits in the
    in-memory room_messages dict permanently. Run this on the same interval
    as the other jobs to reclaim those."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        expired_rooms = (
            db.query(StudyRoom)
            .filter(StudyRoom.status == StudyRoomStatusEnum.active)
            .filter(StudyRoom.timer_ends_at < now)
            .all()
        )
        for room in expired_rooms:
            help_request = room.help_request
            requester_id = help_request.requester_id if help_request else None

            room.status = StudyRoomStatusEnum.closed
            if help_request is not None:
                help_request.status = HelpRequestStatusEnum.closed
                help_request.is_archived = True
            _emit_room_events(db, room, "updated", hr_action="deleted" if help_request else None)
            db.commit()

            _teardown_daily_room(room)
            if _event_loop is not None:
                future = asyncio.run_coroutine_threadsafe(
                    _close_room_connections(room.room_id, requester_id=requester_id),
                    _event_loop,
                )
                try:
                    future.result(timeout=5)
                except Exception:
                    logger.exception("Failed to tear down connections for expired room %s", room.room_id)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _event_loop
    seed_classes()
    seed_shop_items()
    seed_badge_rules()
    seed_dev_data()
    seed_second_teacher_data()
    seed_more_cs_students()
    scheduler.add_job(check_pending_grades, "interval", days=1)
    scheduler.add_job(check_overdue_assignments, "interval", days=1)
    scheduler.add_job(check_expired_rooms, "interval", minutes=5)
    scheduler.start()

    loop = asyncio.get_event_loop()
    _event_loop = loop
    start_listener(loop)
    delivery_task = asyncio.create_task(deliver_loop(room_registry, room_messages))
    notifications_task = asyncio.create_task(deliver_notifications())
    data_events_task = asyncio.create_task(deliver_data_events())

    yield

    delivery_task.cancel()
    notifications_task.cancel()
    data_events_task.cancel()
    stop_listener()
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

# Wildcard origins widen the blast radius of a stolen bearer token — any
# origin could call the API with it. CORS_ORIGINS is a comma-separated list;
# defaults cover the Vite dev server so local dev keeps working unconfigured.
_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail if isinstance(exc.detail, str) else str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    # str(exc) renders Pydantic's full error list — field paths, expected
    # types, and the actual invalid input values — straight to the client.
    # Log that detail server-side instead and return a generic message.
    logging.getLogger(__name__).info(
        "Validation error on %s %s: %s", request.method, request.url.path, exc
    )
    return JSONResponse(status_code=422, content={"message": "Invalid request."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    # Without this, an unhandled exception falls through to Starlette's
    # ServerErrorMiddleware, which builds its 500 response outside of
    # CORSMiddleware — the browser then sees a CORS error instead of the
    # real 500, which hides the actual bug.
    logging.getLogger(__name__).exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"message": "Internal server error."})


@app.get("/")
def health_check():
    return {"status": "ok"}


app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(schools_router, prefix="/api", tags=["schools"])
app.include_router(classes_router, prefix="/api", tags=["classes"])
app.include_router(class_requests_router, prefix="/api", tags=["class-requests"])
app.include_router(sections_router, prefix="/api", tags=["sections"])
app.include_router(enrollment_requests_router, prefix="/api", tags=["enrollment-requests"])
app.include_router(unenroll_requests_router, prefix="/api", tags=["unenroll-requests"])
app.include_router(assignments_router, prefix="/api", tags=["assignments"])
app.include_router(submissions_router, prefix="/api", tags=["submissions"])
app.include_router(quests_router, prefix="/api", tags=["quests"])
app.include_router(quest_completions_router, prefix="/api", tags=["quest-completions"])
app.include_router(points_router, prefix="/api", tags=["points"])
app.include_router(help_requests_router, prefix="/api", tags=["help-requests"])
app.include_router(rooms_router, prefix="/api", tags=["rooms"])
app.include_router(notifications_router, prefix="/api", tags=["notifications"])
app.include_router(users_router, prefix="/api", tags=["users"])
app.include_router(resources_router, prefix="/api", tags=["resources"])
app.include_router(assignment_fit_router, prefix="/api", tags=["assignment-fit"])
app.include_router(shop_router, prefix="/api", tags=["shop"])
