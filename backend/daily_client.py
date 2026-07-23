"""Thin wrapper around the Daily.co REST API for study-room video/voice calls.

Mirrors gemini_advisor.py's shape: a plain httpx wrapper (no SDK), an
is_configured() escape hatch so the feature degrades gracefully when no API
key is set, and callers are expected to catch failures themselves — a Daily
outage should never block chat, which is the room's core feature.
"""

import os

import httpx

DAILY_API_BASE = "https://api.daily.co/v1"
DAILY_TIMEOUT_SECONDS = 15.0

# Safety-net expiry on the Daily side, on top of our own explicit teardown —
# covers the case where our delete call never fires (crash, deploy, bug).
ROOM_EXPIRY_BUFFER_SECONDS = 60 * 60


def is_configured() -> bool:
    return bool(os.getenv("DAILY_API_KEY"))


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ['DAILY_API_KEY']}",
        "Content-Type": "application/json",
    }


def create_room(room_name: str, expires_at_ts: int) -> dict:
    """Creates a private Daily room. Only holders of a meeting token minted
    via create_meeting_token() can join — the room name/URL alone isn't
    enough, so it's fine to expose room_url to the frontend."""
    body = {
        "name": room_name,
        "privacy": "private",
        "properties": {
            "exp": expires_at_ts + ROOM_EXPIRY_BUFFER_SECONDS,
            "enable_chat": False,
            "eject_at_room_exp": True,
        },
    }
    response = httpx.post(
        f"{DAILY_API_BASE}/rooms",
        headers=_headers(),
        json=body,
        timeout=DAILY_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def delete_room(room_name: str) -> None:
    response = httpx.delete(
        f"{DAILY_API_BASE}/rooms/{room_name}",
        headers=_headers(),
        timeout=DAILY_TIMEOUT_SECONDS,
    )
    if response.status_code == 404:
        return
    response.raise_for_status()


def create_meeting_token(room_name: str, user_name: str, is_owner: bool, expires_at_ts: int) -> str:
    body = {
        "properties": {
            "room_name": room_name,
            "user_name": user_name,
            "is_owner": is_owner,
            "exp": expires_at_ts,
        }
    }
    response = httpx.post(
        f"{DAILY_API_BASE}/meeting-tokens",
        headers=_headers(),
        json=body,
        timeout=DAILY_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["token"]
