from typing import Annotated
from uuid import UUID
from fastapi import Depends, Query
from sqlalchemy.orm import Session
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal

from computor_backend.database import get_db
from computor_backend.api.api_builder import CrudRouter
from computor_backend.api.exceptions import ForbiddenException, NotFoundException
from computor_backend.interfaces import CourseInterface
from computor_backend.model import Course
from computor_backend.services.storage_service import get_storage_service
from computor_backend.business_logic.cascade_deletion import delete_course_cascade
from computor_types.cascade_deletion import CascadeDeleteResult

course_router = CrudRouter(CourseInterface)


@course_router.router.delete(
    "/{course_id}",
    response_model=CascadeDeleteResult,
    summary="Delete course and all course-specific data",
    description="""
    Delete a course and ALL its data including:
    - All course members (NOT the users themselves)
    - All course groups
    - All course content types and contents
    - All submission groups and their artifacts
    - All results and grades
    - All messages targeted to the course

    **WARNING**: This is a destructive operation. Use dry_run=true to preview.
    """
)
async def delete_course_endpoint(
    course_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    dry_run: bool = Query(
        default=False,
        description="If true, only returns preview without deleting"
    ),
) -> CascadeDeleteResult:
    """Delete course and all course-specific data."""
    if not permissions.is_admin:
        raise ForbiddenException("Deletion requires admin permissions")

    # Verify course exists
    course = db.query(Course).filter(Course.id == str(course_id)).first()
    if not course:
        raise NotFoundException(f"Course not found: {course_id}")

    storage = get_storage_service()
    result = await delete_course_cascade(
        db=db,
        course_id=str(course_id),
        storage=storage,
        dry_run=dry_run
    )

    return result
