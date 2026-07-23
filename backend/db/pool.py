import os
import time
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

# Session-mode pooler (port 5432). Supabase hard-caps this database at 15
# concurrent client sessions total on this mode, shared across every
# developer's local backend instance. Only db/ws_broadcast.py's permanent
# LISTEN/NOTIFY connection uses this URL directly — LISTEN/NOTIFY needs a
# connection pinned for its whole lifetime, which transaction-mode pooling
# can't provide.
DATABASE_URL = os.getenv("DATABASE_URL")

# Transaction-mode pooler (port 6543), used for the engine below. A
# transaction-mode connection is returned to Supavisor's pool as soon as
# each transaction commits instead of being pinned for the whole client
# session, so a short-lived process (a pytest run, a restarted dev server)
# stops holding a slot from the scarce session-mode cap the moment it exits
# — that cap was getting exhausted by ordinary test/dev traffic alone.
# Same host/user/password as DATABASE_URL, just a different port, so it's
# derived automatically; override with DATABASE_POOL_URL if yours differs.
DATABASE_POOL_URL = os.getenv("DATABASE_POOL_URL") or DATABASE_URL.replace(":5432/", ":6543/", 1)


def _connect_with_retry():
    """Bursts of requests can transiently exceed Supavisor's connection
    ceiling even with a small pool size, but the earlier logged occurrences
    all cleared within about a second — so retry briefly with backoff before
    giving up, instead of failing the request outright."""
    delay = 0.25
    for attempt in range(4):
        try:
            return psycopg2.connect(DATABASE_POOL_URL)
        except psycopg2.OperationalError as exc:
            if attempt == 3 or "max clients reached" not in str(exc):
                raise
            time.sleep(delay)
            delay *= 2


# pool_size + max_overflow must stay well under the connection ceiling or
# the app itself causes connection-refused errors under any moderate
# concurrent load — kept small since multiple developers run instances
# against this same shared database at once.
engine = create_engine(
    DATABASE_POOL_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=3,
    creator=_connect_with_retry,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
