from datetime import datetime, timezone, timedelta
from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.pool import get_db
from dependencies import get_current_user, require_role
from models.enrollment_model import Enrollment
from models.help_request_model import HelpRequest, HelpRequestAcceptance, HelpRequestStatusEnum
from models.notification_model import Notification, NotificationTypeEnum
from models.point_transaction_model import PointTransaction, TransactionSourceEnum
from models.section_model import Section
from models.study_room_model import StudyRoom, RoomMember
from models.user_model import User, RoleEnum
from schemas.help_request import (
    AcceptedByEntry,
    HelpRequestConfirmCreate,
    HelpRequestCreate,
    HelpRequestStudentResponse,
    HelpRequestTeacherResponse,
    HelpRequestAcceptResponse,
    HelpRequestConfirmResponse,
)

router = APIRouter(tags=["help-requests"])

HELP_SESSION_POINTS = 25


def _check_section_access(section_id: int, current_user: User, db: Session) -> Section:
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

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

    return section


def _build_teacher_response(hr: HelpRequest) -> HelpRequestTeacherResponse:
    return HelpRequestTeacherResponse(
        help_request_id=hr.help_request_id,
        requester_id=hr.requester_id,
        requester_username=hr.requester.username,
        topic=hr.topic,
        description=hr.description,
        group_size=hr.group_size,
        current_size=hr.current_size,
        duration_minutes=hr.duration_minutes,
        status=hr.status,
        accepted_by=[
            AcceptedByEntry(
                user_id=a.user_id,
                username=a.user.username,
                accepted_at=a.accepted_at,
            )
            for a in hr.acceptances
        ],
        room_id=hr.room_id,
        created_at=hr.created_at,
    )


@router.get("/sections/{section_id}/help-requests")
def list_help_requests(
    section_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Union[List[HelpRequestStudentResponse], List[HelpRequestTeacherResponse]]:
    _check_section_access(section_id, current_user, db)

    help_requests = (
        db.query(HelpRequest)
        .filter(
            HelpRequest.section_id == section_id,
            HelpRequest.is_archived == False,
        )
        .order_by(HelpRequest.created_at.desc())
        .all()
    )

    if current_user.role == RoleEnum.student:
        return [HelpRequestStudentResponse.model_validate(hr) for hr in help_requests]
    return [_build_teacher_response(hr) for hr in help_requests]


@router.post("/sections/{section_id}/help-requests", response_model=HelpRequestStudentResponse, status_code=201)
def create_help_request(
    section_id: int,
    body: HelpRequestCreate,
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db),
):
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    enrolled = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.student_id == current_user.user_id,
        Enrollment.is_archived == False,
    ).first()
    if not enrolled:
        raise HTTPException(status_code=403, detail="Not enrolled in this section.")

    help_request = HelpRequest(
        section_id=section_id,
        requester_id=current_user.user_id,
        topic=body.topic,
        description=body.description,
        group_size=body.group_size,
        duration_minutes=body.duration_minutes,
    )
    db.add(help_request)
    db.commit()
    db.refresh(help_request)
    return help_request


@router.post("/help-requests/{help_request_id}/accept", response_model=HelpRequestAcceptResponse)
def accept_help_request(
    help_request_id: int,
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db),
):
    help_request = db.query(HelpRequest).filter(
        HelpRequest.help_request_id == help_request_id,
        HelpRequest.is_archived == False,
    ).first()
    if not help_request:
        raise HTTPException(status_code=404, detail="Help request not found.")
    if help_request.status != HelpRequestStatusEnum.open:
        raise HTTPException(status_code=409, detail="Help request is no longer open.")
    if help_request.current_size >= help_request.group_size:
        raise HTTPException(status_code=409, detail="Help request is already full.")
    if help_request.requester_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot accept your own help request.")

    section = db.query(Section).filter(
        Section.section_id == help_request.section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=403, detail="Access denied.")

    enrolled = db.query(Enrollment).filter(
        Enrollment.section_id == help_request.section_id,
        Enrollment.student_id == current_user.user_id,
        Enrollment.is_archived == False,
    ).first()
    if not enrolled:
        raise HTTPException(status_code=403, detail="Not enrolled in this section.")

    already_accepted = db.query(HelpRequestAcceptance).filter(
        HelpRequestAcceptance.help_request_id == help_request_id,
        HelpRequestAcceptance.user_id == current_user.user_id,
    ).first()

    # Create study room on first acceptance; add members on subsequent accepts
    if help_request.study_room is None:
        room = StudyRoom(
            help_request_id=help_request_id,
            timer_ends_at=datetime.now(timezone.utc) + timedelta(minutes=help_request.duration_minutes),
        )
        db.add(room)
        db.flush()
        db.add(RoomMember(room_id=room.room_id, user_id=help_request.requester_id))
    else:
        room = help_request.study_room

    existing_member = db.query(RoomMember).filter(
        RoomMember.room_id == room.room_id,
        RoomMember.user_id == current_user.user_id,
    ).first()
    if existing_member:
        raise HTTPException(status_code=409, detail="Already a member of this room.")

    # A student who accepted before and later left has an existing acceptance
    # record but no room membership — let them rejoin without recording a
    # second acceptance (points/history already reflect their original accept).
    if not already_accepted:
        db.add(HelpRequestAcceptance(
            help_request_id=help_request_id,
            user_id=current_user.user_id,
        ))

    db.add(RoomMember(room_id=room.room_id, user_id=current_user.user_id))
    db.flush()

    help_request.current_size = db.query(RoomMember).filter(RoomMember.room_id == room.room_id).count()
    if help_request.current_size >= help_request.group_size:
        help_request.status = HelpRequestStatusEnum.active

    db.add(Notification(
        user_id=help_request.requester_id,
        type=NotificationTypeEnum.help_request_accepted,
        message="Your help request has been accepted. Your study room is ready.",
    ))

    db.commit()
    db.refresh(room)
    return HelpRequestAcceptResponse(
        help_request_id=help_request_id,
        status=help_request.status,
        room_id=room.room_id,
    )


@router.post("/help-requests/{help_request_id}/drop")
def drop_help_request(
    help_request_id: int,
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db),
):
    help_request = db.query(HelpRequest).filter(
        HelpRequest.help_request_id == help_request_id,
        HelpRequest.is_archived == False,
    ).first()
    if not help_request:
        raise HTTPException(status_code=404, detail="Help request not found.")
    if help_request.requester_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Only the requester can drop this help request.")

    help_request.status = HelpRequestStatusEnum.closed
    help_request.is_archived = True
    db.commit()
    return {"message": "Help request closed."}


@router.post("/help-requests/{help_request_id}/confirm", response_model=HelpRequestConfirmResponse)
def confirm_session(
    help_request_id: int,
    body: HelpRequestConfirmCreate,
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db),
):
    # Not filtered by is_archived: closing/deleting the room archives the help
    # request immediately (to drop it off the bulletin board), but the
    # requester still needs to answer the "did this happen?" prompt afterward
    # to actually get points awarded.
    help_request = db.query(HelpRequest).filter(
        HelpRequest.help_request_id == help_request_id,
    ).first()
    if not help_request:
        raise HTTPException(status_code=404, detail="Help request not found.")
    if help_request.requester_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Only the requester can confirm the session.")

    if body.session_occurred:
        already_confirmed = db.query(PointTransaction).filter(
            PointTransaction.source == TransactionSourceEnum.help_request,
            PointTransaction.source_id == help_request_id,
        ).first()
        if already_confirmed:
            raise HTTPException(status_code=409, detail="Session already confirmed.")

    points_awarded = 0

    if body.session_occurred:
        points_awarded = HELP_SESSION_POINTS
        participant_ids = [help_request.requester_id] + [a.user_id for a in help_request.acceptances]

        for uid in participant_ids:
            participant = db.query(User).filter(User.user_id == uid).first()
            if participant:
                db.add(PointTransaction(
                    user_id=uid,
                    amount=HELP_SESSION_POINTS,
                    source=TransactionSourceEnum.help_request,
                    source_id=help_request_id,
                ))
                participant.total_points += HELP_SESSION_POINTS

    db.commit()
    return HelpRequestConfirmResponse(
        help_request_id=help_request_id,
        session_occurred=body.session_occurred,
        points_awarded=points_awarded,
    )
