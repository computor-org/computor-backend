"""
API endpoints for course member grading statistics.

This module provides REST endpoints for retrieving aggregated progress
and grading statistics for course members.
"""

from uuid import UUID
from typing import Annotated, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.redis_cache import get_cache
from computor_backend.cache import Cache
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.auth import get_current_principal

from computor_types.course_member_gradings import (
    CourseMemberGradingsGet,
    CourseMemberGradingsList,
    CourseMemberGradingsQuery,
)

from computor_backend.business_logic.course_member_gradings import (
    get_course_member_gradings,
    list_course_member_gradings,
)

course_member_gradings_router = APIRouter()


@course_member_gradings_router.get(
    "",
    response_model=List[CourseMemberGradingsList],
    summary="List course member grading statistics for a course",
    description="""
Get aggregated grading and progress statistics for all course members (students) in a course.

Returns full course content hierarchy with submission progress for each student.

**Required Parameter:**
- `course_id`: The course ID (required)

**Returns:**
- Full hierarchical grading stats for each student
- Breakdown by content type (mandatory, optional, etc.)
- Progress percentages at all levels
- Latest submission dates

**Access Control:**
- Admins: Can access any course
- Tutors and higher: Can access courses they are assigned to

**Caching:**
- Results are cached for 30 minutes per student
- Cache automatically invalidates on submissions and grading changes
""",
)
async def list_course_member_gradings_endpoint(
    course_id: str = Query(..., description="Course ID (required)"),
    permissions: Annotated[Principal, Depends(get_current_principal)] = None,
    params: CourseMemberGradingsQuery = Depends(),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
) -> List[CourseMemberGradingsList]:
    """
    List grading statistics for all course members in a course.

    Args:
        course_id: The course ID (required)
        permissions: Current user permissions
        params: Query parameters for filtering
        db: Database session
        cache: Cache instance

    Returns:
        List of CourseMemberGradingsList with aggregated statistics per member
    """
    return await list_course_member_gradings(
        course_id=course_id,
        permissions=permissions,
        params=params,
        db=db,
        cache=cache,
    )


@course_member_gradings_router.get(
    "/{course_member_id}",
    response_model=CourseMemberGradingsGet,
    summary="Get course member grading statistics",
    description="""
Get aggregated grading and progress statistics for a specific course member.

Returns full course content hierarchy with detailed submission progress.

**Calculations:**
- **Full hierarchy**: All course content levels (no filtering)
- **Per ltree layer**: Maximum assignments vs. submitted assignments at each level
- **Per content_type**: Breakdown by mandatory, optional, etc.
- **Progress percentages**: Calculated at every hierarchical level
- **Latest submissions**: Most recent submission date per level

**Access Control:**
- Admins: Can access any course member
- Tutors and higher: Can access members in courses they are assigned to

**Caching:**
- Results are cached for 30 minutes
- Cache automatically invalidates on submissions and grading changes
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
