from fastapi import HTTPException

FULL_NAME_MAX_LENGTH = 100
PASSWORD_MIN_LENGTH = 8


def validate_new_password(raw: str) -> str:
    """Shared minimum-strength check for anywhere a new password is set
    (self-service change, admin reset). Not stripped — leading/trailing
    whitespace in a password is the user's choice, not a typo to clean up.
    """
    if len(raw) < PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {PASSWORD_MIN_LENGTH} characters.",
        )
    return raw


def validate_full_name(raw: str) -> str:
    """Shared full_name validation for registration and profile updates.

    Requires at least one whitespace character (i.e. a first and last name)
    rather than a single word, since a full name is meant to be an actual
    name, not just a repeat of the username.
    """
    full_name = raw.strip()
    if not full_name:
        raise HTTPException(status_code=400, detail="Full name cannot be empty.")
    if len(full_name) > FULL_NAME_MAX_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Full name must be {FULL_NAME_MAX_LENGTH} characters or fewer.",
        )
    if not any(c.isspace() for c in full_name):
        raise HTTPException(
            status_code=400,
            detail="Full name must include at least one space (e.g. a first and last name).",
        )
    return full_name
