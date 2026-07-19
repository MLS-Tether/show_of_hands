import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from assignment_fit import build_section_snapshot
from db.pool import get_db
from dependencies import require_role
from gemini_advisor import generate_fit_verdict, is_configured
from models.section_model import Section
from models.user_model import User
from schemas.assignment_fit import AssignmentDraft, AssignmentFitResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["assignment-fit"])


@router.post("/sections/{section_id}/assignment-fit", response_model=AssignmentFitResponse)
def check_assignment_fit(
    section_id: int,
    body: AssignmentDraft,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    if section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")

    snapshot = build_section_snapshot(db, section_id)

    if snapshot["graded_submission_count"] == 0:
        return AssignmentFitResponse(
            ai_available=False,
            unavailable_reason="insufficient_data",
            stats=snapshot,
        )

    if not is_configured():
        raise HTTPException(status_code=503, detail="AI advisor is not configured.")

    draft = body.model_dump(mode="json")
    try:
        verdict = generate_fit_verdict(draft, snapshot)
    except Exception:
        logger.exception("Assignment-fit Gemini call failed for section %s", section_id)
        return AssignmentFitResponse(
            ai_available=False,
            unavailable_reason="error",
            stats=snapshot,
        )

    return AssignmentFitResponse(ai_available=True, verdict=verdict, stats=snapshot)
