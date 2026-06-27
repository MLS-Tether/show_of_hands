from fastapi import APIRouter, Depends

from dependencies import require_role
from models.user_model import User
from schemas.school import SchoolResponse, SchoolCodeResponse

router = APIRouter(prefix="/schools", tags=["schools"])


@router.get("/code", response_model=SchoolCodeResponse)
def get_school_code(
    current_user: User = Depends(require_role(["admin"])),
):
    return SchoolCodeResponse(school_code=current_user.school.school_code)


@router.get("/me", response_model=SchoolResponse)
def get_my_school(
    current_user: User = Depends(require_role(["student", "teacher", "admin"])),
):
    return current_user.school
