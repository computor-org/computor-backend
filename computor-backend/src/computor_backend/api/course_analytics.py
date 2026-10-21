"""
Lecturer analytics endpoints: typical errors, student activity and flags.

All three are course-wide reports over every student's work, so they share
the floor of ``course_member_gradings``: lecturer or higher in the course
(admins anywhere). Tutors grade through ``/tutors``; they do not get these.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from computor_types.course_analytics import (
    CourseFlagsGet,
    StudentActivityGet,
    TypicalErrorsGet,
)
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from computor_backend.business_logic.course_analytics import (
    DEFAULT_SESSION_GAP_MINUTES,
    get_course_flags,
    get_student_activity,
    get_typical_errors,
)
from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal

course_analytics_router = APIRouter()

_DUE_AT = Query(
    None,
    description=(
        "Due date to relate submissions to (ISO 8601). The platform stores no "
        "deadlines, so the caller supplies the one set on the page."
    ),
)


@course_analytics_router.get(
    "/courses/{course_id}/typical-errors",
    response_model=TypicalErrorsGet,
    summary="Typical errors of a course or one assignment",
)
async def course_typical_errors_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    course_content_id: str | None = Query(None, description="Limit to one assignment"),
    max_results: int = Query(300, ge=1, le=2000, description="Newest imperfect test runs to scan"),
    db: Session = Depends(get_db, scope="function"),
) -> TypicalErrorsGet:
    """Failing tests grouped by normalized message, with affected students and examples."""
    return await get_typical_errors(
        str(course_id),
        permissions,
        db,
        course_content_id=course_content_id,
        max_results=max_results,
    )


@course_analytics_router.get(
    "/courses/{course_id}/flags",
    response_model=CourseFlagsGet,
    summary="Rule-based flags for every student of a course",
)
async def course_flags_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    due_at: datetime | None = _DUE_AT,
    db: Session = Depends(get_db, scope="function"),
) -> CourseFlagsGet:
    return await get_course_flags(str(course_id), permissions, db, due_at=due_at)


@course_analytics_router.get(
    "/course-members/{course_member_id}/activity",
    response_model=StudentActivityGet,
    summary="History, attempt timeline and flags of one student",
)
async def student_activity_endpoint(
    course_member_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    due_at: datetime | None = _DUE_AT,
    session_gap_minutes: int = Query(
        DEFAULT_SESSION_GAP_MINUTES,
        ge=5,
        le=240,
        description="Runs closer than this count as one working session for the time estimate",
    ),
    db: Session = Depends(get_db, scope="function"),
) -> StudentActivityGet:
    return await get_student_activity(
        str(course_member_id),
        permissions,
        db,
        due_at=due_at,
        session_gap_minutes=session_gap_minutes,
    )
