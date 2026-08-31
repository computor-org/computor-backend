import logging
import os
from contextlib import contextmanager
from typing import Callable, Generator, TYPE_CHECKING
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import sqlalchemy.exc as sa_exc
from fastapi import Depends

if TYPE_CHECKING:
    from computor_backend.permissions.principal import Principal

logger = logging.getLogger(__name__)

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_DB = os.environ.get("POSTGRES_DB")

DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

_statement_timeout_ms = int(os.environ.get("DB_STATEMENT_TIMEOUT_MS", "30000"))  # 30s default

_engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,     # 30 min - protects against idle disconnects
    pool_pre_ping=True,    # avoids stale connections
    pool_use_lifo=True,
    future=True,
    connect_args={"options": f"-c statement_timeout={_statement_timeout_ms}"},
)

SessionLocal: Callable[[], Session] = sessionmaker(
    bind=_engine,
    autocommit=False,
    expire_on_commit=False,  # more convenient with Pydantic
    autoflush=False,         # prevents "accidental" DB touching
    class_=Session
)


# ---------------------------------------------------------------------------
# Deferred post-commit side effects (cache invalidation).
#
# Repositories flush (not commit) inside a request, so the request is a single
# unit of work committed once by ``get_db``/``get_db_session``. Cache
# invalidation must therefore run only when the write actually lands: callbacks
# registered via ``register_post_commit`` fire on the session's ``after_commit``
# event (works for the request-end commit AND any explicit mid-request commit)
# and are dropped on rollback so a rolled-back write never evicts a live entry.
# ---------------------------------------------------------------------------

_POST_COMMIT_KEY = "post_commit_callbacks"


def register_post_commit(db: Session, callback: Callable[[], None]) -> None:
    """Queue ``callback`` to run after the session's next successful commit."""
    db.info.setdefault(_POST_COMMIT_KEY, []).append(callback)


@event.listens_for(SessionLocal, "after_commit")
def _run_post_commit_callbacks(session: Session) -> None:
    callbacks = session.info.pop(_POST_COMMIT_KEY, None)
    if not callbacks:
        return
    for callback in callbacks:
        try:
            callback()
        except Exception:  # cache invalidation must never break the request
            logger.warning("post-commit callback failed", exc_info=True)


@event.listens_for(SessionLocal, "after_rollback")
def _drop_post_commit_callbacks(session: Session) -> None:
    session.info.pop(_POST_COMMIT_KEY, None)


# ---------------------------------------------------------------------------
# Permission-affecting writes (#384).
#
# The Principal cache is keyed by the raw credential token, so a mutation of
# SOMEONE ELSE's permissions cannot delete the affected entries directly.
# Instead: any ORM flush that touches a membership table records the affected
# user ids here, and after the commit lands each of those users gets a
# per-user stale stamp + a ``permissions:updated`` websocket push (see
# permissions/principal_invalidation.py). Hooking the session — rather than
# each endpoint — covers CrudRouter, invites, member import and Temporal
# activities in every process that uses this session factory. Bulk
# ``query(...).update()`` writes bypass flush events and must invalidate
# explicitly (business_logic/user_connect.py does).
# ---------------------------------------------------------------------------

_PERMISSION_STALE_KEY = "permission_stale_user_ids"


def _permission_membership_models() -> tuple:
    # Imported lazily: model modules import heavily and importing them at
    # database-module import time would create a cycle.
    from computor_backend.model.course import CourseFamilyMember, CourseMember
    from computor_backend.model.organization import OrganizationMember
    from computor_backend.model.role import UserRole

    return (UserRole, CourseMember, OrganizationMember, CourseFamilyMember)


@event.listens_for(SessionLocal, "after_flush")
def _track_permission_membership_writes(session: Session, flush_context) -> None:
    # ``new``/``dirty``/``deleted`` still show the pre-flush state here.
    membership_models = _permission_membership_models()
    affected = None
    for obj in session.new.union(session.dirty).union(session.deleted):
        if isinstance(obj, membership_models):
            user_id = getattr(obj, "user_id", None)
            if user_id is not None:
                if affected is None:
                    affected = session.info.setdefault(_PERMISSION_STALE_KEY, set())
                affected.add(str(user_id))


@event.listens_for(SessionLocal, "after_commit")
def _invalidate_stale_principals(session: Session) -> None:
    user_ids = session.info.pop(_PERMISSION_STALE_KEY, None)
    if not user_ids:
        return
    try:
        from computor_backend.permissions.principal_invalidation import (
            invalidate_user_principals,
        )

        invalidate_user_principals(user_ids)
    except Exception:  # cache invalidation must never break the request
        logger.warning("Principal invalidation after commit failed", exc_info=True)


@event.listens_for(SessionLocal, "after_rollback")
def _drop_stale_principal_tracking(session: Session) -> None:
    session.info.pop(_PERMISSION_STALE_KEY, None)

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


get_db_session = contextmanager(_get_db)
"""Context manager for non-FastAPI code (startup, websockets, temporal tasks).

Usage:
    with get_db_session() as db:
        ...
    # commit/rollback/close handled automatically
"""


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
        from computor_backend.exceptions import ServiceUnavailableException
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