import asyncio
import json
import select
import threading
from typing import Optional

import psycopg2
from sqlalchemy import text

from db.pool import DATABASE_URL

CHANNEL_NAME = "room_chat_channel"

broadcast_queue: asyncio.Queue = asyncio.Queue()

_stop_event = threading.Event()
_listener_thread: Optional[threading.Thread] = None


def _listen_loop(loop: asyncio.AbstractEventLoop):
    """Runs in a background thread. Blocks waiting for Postgres NOTIFY events
    and hands each payload off to the asyncio event loop via a thread-safe call."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"LISTEN {CHANNEL_NAME};")

    try:
        while not _stop_event.is_set():
            if select.select([conn], [], [], 5) == ([], [], []):
                continue
            conn.poll()
            while conn.notifies:
                notify = conn.notifies.pop(0)
                loop.call_soon_threadsafe(broadcast_queue.put_nowait, notify.payload)
    finally:
        cur.close()
        conn.close()


def start_listener(loop: asyncio.AbstractEventLoop):
    global _listener_thread
    _stop_event.clear()
    _listener_thread = threading.Thread(target=_listen_loop, args=(loop,), daemon=True)
    _listener_thread.start()


def stop_listener():
    _stop_event.set()


async def deliver_loop(room_registry: dict):
    """Runs as an asyncio task. Reads relayed messages off the queue and
    delivers them to any locally-connected WebSocket clients in that room."""
    while True:
        raw_payload = await broadcast_queue.get()
        try:
            data = json.loads(raw_payload)
        except json.JSONDecodeError:
            continue

        room_id = data.pop("room_id", None)
        sender_id = data.pop("sender_id", None)
        if room_id is None:
            continue

        dead_connections = []
        for other_user_id, other_ws in list(room_registry.get(room_id, {}).items()):
            if other_user_id == sender_id:
                continue
            try:
                await other_ws.send_json(data)
            except Exception:
                dead_connections.append(other_user_id)

        for dead_id in dead_connections:
            room_registry.get(room_id, {}).pop(dead_id, None)


def notify_room_message(db, room_id: int, message_out: dict, sender_id: int):
    """Call this instead of broadcasting directly. Fires a Postgres NOTIFY
    that every listening backend process (including this one) will receive."""
    payload = json.dumps({"room_id": room_id, "sender_id": sender_id, **message_out})
    db.execute(text("SELECT pg_notify(:channel, :payload)"), {"channel": CHANNEL_NAME, "payload": payload})
    db.commit()
