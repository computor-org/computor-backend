"""API endpoints for course member import."""
import logging
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.business_logic.course_member_import import import_course_member

from computor_types.course_member_import import (
    CourseMemberImportRequest,
    CourseMemberImportResponse,
)

logger = logging.getLogger(__name__)

course_member_import_router = APIRouter(
    prefix="/course-member-import",
    tags=["course-member-import"]
)


@course_member_import_router.post(
    "/{course_id}",
    response_model=CourseMemberImportResponse,
)
async def import_member(
    course_id: str,
    request: CourseMemberImportRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)] = None,
    db: Session = Depends(get_db),
) -> CourseMemberImportResponse:
    """Import a course member.

    This endpoint accepts a member's data and imports them into the specified course.
    If the member already exists, they will be updated.

    **Required Permissions**: Lecturer role or higher (_lecturer, _maintainer, _owner)

    Args:
        course_id: ID of the course to import member into
        request: Member data including email, name, group, and role
        permissions: Current user's permissions
        db: Database session

    Returns:
        Import response with created/updated course member and created group (if any)

    Raises:
        ForbiddenException: If user lacks lecturer role or higher
        BadRequestException: If validation fails
    """
    logger.info(f"Importing member {request.email} to course {course_id}")

    try:
        result = await import_course_member(
            course_id=course_id,
            member_request=request,
            permissions=permissions,
            db=db,
            username_strategy="name",  # Use name-based username generation by default
        )

        # Commit transaction if successful
        if result.success:
            db.commit()
            logger.info(f"Member import successful: {request.email}")
        else:
            db.rollback()
            logger.warning(f"Member import failed: {result.message}")

        return result

    except Exception as e:
        db.rollback()
        logger.error(f"Member import failed: {e}", exc_info=True)
        raise
