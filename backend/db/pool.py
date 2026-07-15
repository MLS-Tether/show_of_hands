import os
import time
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def _connect_with_retry():
    """Supabase's session-mode pooler hard-caps this database at 15
    concurrent client sessions total, shared across every developer's local
    backend instance (each of which also holds one permanent connection open
    outside this pool for LISTEN/NOTIFY in db/ws_broadcast.py). Bursts of
    requests can transiently exceed that ceiling even with a small pool size,
    but the earlier logged occurrences all cleared within about a second — so
    retry briefly with backoff before giving up, instead of failing the
    request outright."""
    delay = 0.25
    for attempt in range(4):
        try:
            return psycopg2.connect(DATABASE_URL)
        except psycopg2.OperationalError as exc:
            if attempt == 3 or "max clients reached" not in str(exc):
                raise
            time.sleep(delay)
            delay *= 2


# pool_size + max_overflow must stay well under the 15-connection ceiling or
# the app itself causes connection-refused errors under any moderate
# concurrent load — kept small since multiple developers run instances
# against this same shared database at once.
engine = create_engine(
    DATABASE_URL,
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
