from fastapi import HTTPException

FULL_NAME_MAX_LENGTH = 100


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
