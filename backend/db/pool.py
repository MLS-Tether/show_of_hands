import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Supabase's session-mode pooler hard-caps this database at 15 concurrent
# client sessions total (see: "max clients are limited to pool_size: 15"),
# and db/ws_broadcast.py holds one more connection open permanently outside
# this pool for LISTEN/NOTIFY. pool_size + max_overflow must stay well under
# that ceiling or the app itself causes connection-refused errors under any
# moderate concurrent load.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=8, max_overflow=4)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
