import asyncio
import json
import select
import threading
from typing import Optional

import psycopg2
from sqlalchemy import text

from db.pool import DATABASE_URL

CHANNEL_NAME = "room_chat_channel"
NOTIFICATION_CHANNEL_NAME = "user_notifications_channel"
DATA_EVENTS_CHANNEL = "data_events"

broadcast_queue: asyncio.Queue = asyncio.Queue()
notification_queue: asyncio.Queue = asyncio.Queue()
data_events_queue: asyncio.Queue = asyncio.Queue()

_QUEUE_BY_CHANNEL = {
    CHANNEL_NAME: broadcast_queue,
    NOTIFICATION_CHANNEL_NAME: notification_queue,
    DATA_EVENTS_CHANNEL: data_events_queue,
}

_stop_event = threading.Event()
_listener_thread: Optional[threading.Thread] = None


def _listen_loop(loop: asyncio.AbstractEventLoop):
    """Runs in a background thread. Blocks waiting for Postgres NOTIFY events
    on any registered channel and hands each payload off to that channel's
    asyncio queue via a thread-safe call."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    for channel in _QUEUE_BY_CHANNEL:
        cur.execute(f"LISTEN {channel};")

    try:
        while not _stop_event.is_set():
            if select.select([conn], [], [], 5) == ([], [], []):
                continue
            conn.poll()
            while conn.notifies:
                notify = conn.notifies.pop(0)
                queue = _QUEUE_BY_CHANNEL.get(notify.channel)
                if queue is not None:
                    loop.call_soon_threadsafe(queue.put_nowait, notify.payload)
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


async def deliver_loop(room_registry: dict, room_messages: dict):
    """Runs as an asyncio task. Reads relayed messages off the queue and
    delivers them to any locally-connected WebSocket clients in that room.

    Also records genuine chat messages (anything without a "type" key —
    control events like timer_extended/room_deleted are excluded) into this
    process's own room_messages history. This is the ONLY place that writes
    history, on purpose: every backend process listens for every NOTIFY,
    including the one it just issued itself, so a message always round-trips
    back here regardless of which process the sender was connected to. That
    keeps every process's replay history consistent even when different
    members of the same room are connected to different backend instances
    (e.g. two developers each running their own local server against the
    same shared database) — without this, a process would only have replay
    history for messages that originated on itself."""
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

        if "type" not in data:
            room_messages.setdefault(room_id, []).append(data)

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
