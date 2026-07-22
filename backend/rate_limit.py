import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException

from dependencies import get_current_user
from models.user_model import User


def rate_limiter(max_calls: int, window_seconds: float):
    """Per-user sliding-window rate limit dependency. In-memory like the
    notification/room registries elsewhere in this backend — fine for a
    single-process deployment, resets on restart."""
    calls: dict = defaultdict(deque)

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        now = time.monotonic()
        bucket = calls[current_user.user_id]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= max_calls:
            raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")
        bucket.append(now)
        return current_user

    return dependency
