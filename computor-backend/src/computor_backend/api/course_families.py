from types import SimpleNamespace
from typing import Annotated
from uuid import UUID
from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.core import can_perform_action
from computor_backend.permissions.principal import Principal

from computor_backend.database import get_db
from computor_backend.api.api_builder import CrudRouter, invalidate_request_principal
from computor_backend.exceptions import ConflictException, ForbiddenException, NotFoundException
from computor_backend.interfaces import CourseFamilyInterface
from computor_backend.model import Course, CourseFamily
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
    request: Request,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    dry_run: bool = Query(
        default=False,
        description="If true, only returns preview without deleting"
    ),
) -> CascadeDeleteResult:
    """Delete course family — owners and admins only, and only when it has no courses left."""
    fid = str(course_family_id)
    # Through the entity's permission handler (``delete`` -> scope ``_owner``):
    # the same answer the generic route would give. ``_organization_manager``
    # is a manager, not an owner, and deliberately does not pass.
    if not can_perform_action(permissions, CourseFamily, "delete", resource_id=fid):
        raise ForbiddenException(
            detail="Only an owner of this course family (or an administrator) can delete it."
        )

    # Verify course family exists
    family = db.query(CourseFamily).filter(CourseFamily.id == fid).first()
    if not family:
        raise NotFoundException(detail=f"Course family not found: {course_family_id}")

    # Guard: never cascade through courses. A family with courses must be emptied
    # first, otherwise an org/family delete silently orphans student repositories.
    #
    # Deleting a course removes only its template and reference repositories
    # from the git server — the org, the student repositories, the graders team
    # and the per-user clone tokens all survive. Deleting one course at a time
    # keeps that visible and recoverable, rather than losing a whole family's
    # worth of repositories in a single call.
    course_count = db.query(Course).filter(Course.course_family_id == fid).count()
    blocked_reason = None
    if course_count > 0:
        blocked_reason = (
            f"This course family still has {course_count} course"
            f"{'s' if course_count != 1 else ''}. Delete "
            f"{'them' if course_count != 1 else 'it'} first, then delete the family."
        )
    if blocked_reason and not dry_run:
        raise ConflictException(detail=blocked_reason)

    storage = get_storage_service()
    result = await delete_course_family_cascade(
        db=db,
        course_family_id=fid,
        storage=storage,
        dry_run=dry_run
    )
    if dry_run:
        # Tell the client up front what the real call would refuse.
        result.blocked_reason = blocked_reason
        return result

    if not result.errors:
        # The family's scope members went with the row; drop the view caches
        # keyed on it and the caller's own cached roles (they just lost one).
        course_family_router._invalidate_caches_for(
            SimpleNamespace(id=fid, course_family_id=fid)
        )
        await invalidate_request_principal(request, what="deleting a course family")
    return result
