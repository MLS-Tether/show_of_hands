import hashlib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from db.pool import get_db
from auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    RefreshToken,
)
from dependencies import get_current_user, require_role
from models.user_model import User, RoleEnum
from models.school_model import School
from schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    role: str
    user_id: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ResetPasswordRequest(BaseModel):
    user_id: int
    new_password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    school_code: str
    role: RoleEnum
    email: Optional[str] = None


@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    school = db.query(School).filter(School.school_code == body.school_code).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found.")

    existing = (
        db.query(User)
        .filter(
            User.username == body.username,
            User.school_id == school.school_id,
            User.is_archived == False,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken.")

    user = User(
        school_id=school.school_id,
        username=body.username,
        password_hash=hash_password(body.password),
        email=body.email,
        role=body.role,
        is_verified=body.role == RoleEnum.student,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.username == body.username,
        User.is_archived == False,
    ).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Account pending admin verification.")

    access_token = create_access_token(user.user_id, user.role.value, user.school_id)
    refresh_token = create_refresh_token(user.user_id, db)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        role=user.role.value,
        user_id=user.user_id,
    )


@router.post("/refresh")
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    jti = payload.get("jti")
    user_id = payload.get("user_id")
    if not jti or not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    record = db.query(RefreshToken).filter(
        RefreshToken.jti == jti,
        RefreshToken.token_hash == token_hash,
    ).first()
    if not record:
        raise HTTPException(status_code=401, detail="Refresh token not found or already used.")

    user = db.query(User).filter(
        User.user_id == user_id,
        User.is_archived == False,
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")

    access_token = create_access_token(user.user_id, user.role.value, user.school_id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(
    body: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload = decode_token(body.refresh_token)
    jti = payload.get("jti")
    record = db.query(RefreshToken).filter(
        RefreshToken.jti == jti,
        RefreshToken.user_id == current_user.user_id,
    ).first()
    if record:
        db.delete(record)
        db.commit()
    return {"message": "Logged out successfully."}


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    current_user: User = Depends(require_role(["admin", "teacher"])),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(
        User.user_id == body.user_id,
        User.is_archived == False,
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.role != RoleEnum.student:
        raise HTTPException(status_code=403, detail="Can only reset passwords for students.")
    if target.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Cannot reset passwords for users outside your school.")

    target.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password reset successfully."}
