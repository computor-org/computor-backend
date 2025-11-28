"""
API endpoints for course member grading statistics.

This module provides REST endpoints for retrieving aggregated progress
and grading statistics for course members.
"""

from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.redis_cache import get_cache
from computor_backend.cache import Cache
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.auth import get_current_principal

from computor_types.course_member_gradings import (
    CourseMemberGradingsGet,
    CourseMemberGradingsQuery,
)

from computor_backend.business_logic.course_member_gradings import (
    get_course_member_gradings,
)

course_member_gradings_router = APIRouter()


@course_member_gradings_router.get(
    "/{course_member_id}",
    response_model=CourseMemberGradingsGet,
    summary="Get course member grading statistics",
    description="""
Get aggregated grading and progress statistics for a course member.

This endpoint calculates:
- **Per ltree layer**: Maximum assignments available vs. submitted assignments
- **Per course_content_type**: Separate aggregation for different content types
- **Percentage calculations**: Progress percentage at each hierarchical level
- **Latest submission date**: Most recent submitted artifact's created_at

**Access Control:**
- Admins: Can access any course member
- Lecturers/Tutors: Can access members in courses they manage
- Students: Can access their own statistics only
""",
)
async def get_course_member_gradings_endpoint(
    course_member_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseMemberGradingsQuery = Depends(),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
) -> CourseMemberGradingsGet:
    """
    Get grading statistics for a course member.

    Args:
        course_member_id: The course member ID
        permissions: Current user permissions
        params: Query parameters for filtering
        db: Database session
        cache: Cache instance

    Returns:
        CourseMemberGradingsGet with aggregated statistics
    """
    return await get_course_member_gradings(
        course_member_id=course_member_id,
        permissions=permissions,
        params=params,
        db=db,
        cache=cache,
    )
