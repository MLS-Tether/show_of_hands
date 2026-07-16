from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from db.pool import get_db
from auth_utils import decode_token
from models.user_model import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_LAST_ACTIVE_THROTTLE = timedelta(minutes=5)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(token)
    user = db.query(User).filter(User.user_id == payload["user_id"]).first()
    if not user or user.is_archived:
        raise HTTPException(status_code=401, detail="User not found.")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Account pending admin verification.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated.")

    now = datetime.now(timezone.utc)
    if not user.last_active_at or now - user.last_active_at > _LAST_ACTIVE_THROTTLE:
        user.last_active_at = now
        db.commit()

    return user


def require_role(allowed_roles: list):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in allowed_roles:
            raise HTTPException(status_code=403, detail="Unauthorized")
        return current_user
    return dependency

