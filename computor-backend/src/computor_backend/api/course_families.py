from typing import Annotated
from uuid import UUID
from fastapi import Depends, Query
from sqlalchemy.orm import Session
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal

from computor_backend.database import get_db
from computor_backend.api.api_builder import CrudRouter
from computor_backend.api.exceptions import ForbiddenException, NotFoundException
from computor_backend.interfaces import CourseFamilyInterface
from computor_backend.model import CourseFamily
from computor_backend.services.storage_service import get_storage_service
from computor_backend.business_logic.cascade_deletion import delete_course_family_cascade
from computor_types.cascade_deletion import CascadeDeleteResult

course_family_router = CrudRouter(CourseFamilyInterface)


@course_family_router.router.delete(
    "/{course_family_id}",
    response_model=CascadeDeleteResult,
    summary="Delete course family and all descendant courses",
    description="""
    Delete a course family and ALL its descendant data including:
    - All courses in the family
    - All course members, groups, contents, submissions
    - All messages targeted to the family or its courses

    **WARNING**: This is a destructive operation. Use dry_run=true to preview.
    """
)
async def delete_course_family_endpoint(
    course_family_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    dry_run: bool = Query(
        default=False,
        description="If true, only returns preview without deleting"
    ),
) -> CascadeDeleteResult:
    """Delete course family and all descendant courses."""
    if not permissions.is_admin:
        raise ForbiddenException("Deletion requires admin permissions")

    # Verify course family exists
    family = db.query(CourseFamily).filter(CourseFamily.id == str(course_family_id)).first()
    if not family:
        raise NotFoundException(f"Course family not found: {course_family_id}")

    storage = get_storage_service()
    result = await delete_course_family_cascade(
        db=db,
        course_family_id=str(course_family_id),
        storage=storage,
        dry_run=dry_run
    )

    return result
