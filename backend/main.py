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
from db.seed import seed_classes, seed_dev_data, seed_second_teacher_data, seed_more_cs_students
from db.ws_broadcast import start_listener, stop_listener, deliver_loop
from models.assignment_model import Assignment
from models.enrollment_model import Enrollment
from models.submission_model import Submission, SubmissionStatusEnum
from models.notification_model import Notification, NotificationTypeEnum

from controllers.auth_controller import router as auth_router
from controllers.schools_controller import router as schools_router
from controllers.classes_controller import router as classes_router
from controllers.class_requests_controller import router as class_requests_router
from controllers.sections_controller import router as sections_router
from controllers.enrollment_requests_controller import router as enrollment_requests_router
from controllers.assignments_controller import router as assignments_router
from controllers.submissions_controller import router as submissions_router
from controllers.quests_controller import router as quests_router
from controllers.quest_completions_controller import router as quest_completions_router
from controllers.points_controller import router as points_router
from controllers.help_requests_controller import router as help_requests_router
from controllers.rooms_controller import router as rooms_router, room_registry, room_messages
from controllers.notifications_controller import (
    router as notifications_router,
    deliver_notifications,
    deliver_data_events,
)
from controllers.users_controller import router as users_router
from controllers.resources_controller import router as resources_router
from controllers.assignment_fit_controller import router as assignment_fit_router

scheduler = BackgroundScheduler()


def check_pending_grades():
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=10)
        stale_submissions = (
            db.query(Submission)
            .filter(Submission.status == SubmissionStatusEnum.pending)
            .filter(Submission.updated_at <= cutoff)
            .filter(Submission.is_archived == False)
            .all()
        )
        for submission in stale_submissions:
            section = submission.assignment.section
            if section.teacher_id is None:
                continue
            db.add(
                Notification(
                    user_id=section.teacher_id,
                    type=NotificationTypeEnum.grade_finalization_reminder,
                    message=(
                        f"Submission #{submission.submission_id} has been pending "
                        "grading for over 10 days."
                    ),
                )
            )
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

                db.add(Notification(
                    user_id=enrollment.student_id,
                    type=NotificationTypeEnum.assignment_overdue,
                    assignment_id=assignment.assignment_id,
                    message=f"Assignment '{assignment.title}' is overdue.",
                ))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_classes()
    seed_dev_data()
    seed_second_teacher_data()
    seed_more_cs_students()
    scheduler.add_job(check_pending_grades, "interval", days=1)
    scheduler.add_job(check_overdue_assignments, "interval", days=1)
    scheduler.start()

    loop = asyncio.get_event_loop()
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
