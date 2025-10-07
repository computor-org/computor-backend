import os
from typing import Generator, Callable, TYPE_CHECKING
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import sqlalchemy.exc as sa_exc
from fastapi import Depends

if TYPE_CHECKING:
    from computor_backend.permissions.principal import Principal

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
    pool_use_lifo=True,
    future=True
)

SessionLocal: Callable[[], Session] = sessionmaker(
    bind=_engine,
    autocommit=False,
    expire_on_commit=False,  # more convenient with Pydantic
    autoflush=False,         # prevents "accidental" DB touching
    class_=Session
)

def _get_db(user_id: str | None = None) -> Generator[Session, None, None]:
    """
    Internal database session generator with transaction management.

    Handles:
    - Session creation and cleanup
    - User context setting for audit tracking
    - Automatic commit on success
    - Rollback on exceptions

    Args:
        user_id: Optional user ID for audit tracking

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        # Set user context for audit tracking if user_id is provided
        # SET LOCAL is transaction-scoped and automatically resets
        if user_id:
            db.execute(text("SET LOCAL app.user_id = :uid"), {"uid": user_id})

        yield db

        # Only commit if we have an open transaction
        if db.in_transaction():
            db.commit()
    except Exception:
        # Rollback on any exception
        if db.in_transaction():
            db.rollback()
        raise
    finally:
        # Always close the session
        db.close()


def get_db(user_id: str | None = None) -> Generator[Session, None, None]:
    """
    FastAPI dependency: provides a database session with optional user tracking.

    Sets the PostgreSQL app.user_id session variable for automatic audit tracking
    of created_by and updated_by fields. The variable is transaction-scoped and
    automatically resets after commit/rollback.

    Usage:
        # Without user tracking
        @router.get("/public")
        async def public_endpoint(db: Session = Depends(get_db)):
            ...

        # With user tracking (for audit logging)
        @router.post("/resources")
        async def create_resource(
            permissions: Annotated[Principal, Depends(get_current_principal)],
            db: Session = Depends(lambda: get_db(permissions.user_id))
        ):
            # created_by and updated_by will be automatically set
            ...

    Args:
        user_id: Optional user ID to set for audit tracking. If provided,
                 sets the PostgreSQL app.user_id variable which triggers
                 automatic population of created_by/updated_by fields.

    Yields:
        Database session with user context set (if user_id provided)
    """

    try:
        # delegate to the core dependency that manages Session lifecycle
        yield from _get_db(user_id)
    except sa_exc.TimeoutError as e:  # QueuePool acquisition timed out
        # Import here to avoid circular dependency
        from computor_backend.api.exceptions import ServiceUnavailableException
        # 503 is the right code for transient capacity issues
        raise ServiceUnavailableException(
            detail="Database is busy. Please retry shortly.",
            headers={"Retry-After": "2"}  # seconds; tune to your traffic
        ) from e


def set_db_user(db: Session, user_id: str | None):
    """
    Set the user context for a database session.

    This function sets the PostgreSQL app.user_id variable which triggers
    automatic population of created_by/updated_by fields via database triggers.

    Usage in endpoint:
        @router.post("/resources")
        async def create_resource(
            permissions: Annotated[Principal, Depends(get_current_principal)],
            data: ResourceCreate,
            db: Session = Depends(get_db)
        ):
            # Set user context for this session
            set_db_user(db, permissions.user_id)

            resource = MyResource(**data.dict())
            db.add(resource)
            db.commit()
            return resource

    Args:
        db: Database session
        user_id: User ID to set for audit tracking
    """
    if user_id:
        db.execute(text("SET LOCAL app.user_id = :uid"), {"uid": user_id})