from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from apscheduler.schedulers.background import BackgroundScheduler

from db.pool import SessionLocal
from db.seed import seed_classes
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
from controllers.rooms_controller import router as rooms_router
from controllers.notifications_controller import router as notifications_router
from controllers.users_controller import router as users_router

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_classes()
    scheduler.add_job(check_pending_grades, "interval", days=1)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    return JSONResponse(status_code=422, content={"message": str(exc)})


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
