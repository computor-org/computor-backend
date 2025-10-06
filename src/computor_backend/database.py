import os
from typing import Generator, Callable
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_DB = os.environ.get("POSTGRES_DB")

DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

_engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,     # 30 min - protects against idle disconnects
    pool_pre_ping=True,    # avoids stale connections
    future=True
)

SessionLocal: Callable[[], Session] = sessionmaker(
    bind=_engine,
    expire_on_commit=False,  # more convenient with Pydantic
    autoflush=False,         # prevents "accidental" DB touching
    class_=Session
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency: provides a database session.
    Only commits if a transaction is active.
    """
    db = SessionLocal()
    try:
        yield db
        # Only commit if we have an open transaction
        if db.in_transaction():
            db.commit()
    except Exception:
        if db.in_transaction():
            db.rollback()
        raise
    finally:
        db.close()
