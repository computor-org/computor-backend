"""API endpoints for course member import."""
import base64
import logging
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.core import check_course_permissions
from computor_backend.model.course import Course
from computor_backend.business_logic.course_member_import import import_course_member
from computor_backend.business_logic.course_member_import_parse import parse_course_member_file
from computor_backend.exceptions import ForbiddenException, BadRequestException

from computor_types.course_member_import import (
    CourseMemberImportRequest,
    CourseMemberImportResponse,
    CourseMemberImportFileParseRequest,
    CourseMemberImportParseResponse,
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

            # Invalidate user view caches the same way the CrudRouter does
            # for course_member writes — otherwise the target user's cached
            # student/tutor/lecturer list_courses (tagged only by user:<uid>,
            # not by course_id) will keep hiding the new membership until
            # TTL expiry.
            try:
                from computor_backend.cache import get_cache

                cache = get_cache()
                cm = result.course_member or {}
                target_user_id = cm.get("user_id")
                target_course_id = cm.get("course_id")
                if target_user_id:
                    cache.invalidate_user_views(user_id=str(target_user_id))
                if target_course_id:
                    cache.invalidate_user_views(
                        entity_type="course_id",
                        entity_id=str(target_course_id),
                    )
                    for view_tag in ("student_view", "tutor_view", "lecturer_view"):
                        cache.invalidate_user_views(
                            entity_type=view_tag,
                            entity_id=str(target_course_id),
                        )
            except Exception as cache_err:
                logger.warning(
                    f"View cache invalidation after member import failed: {cache_err}"
                )
        else:
            db.rollback()
            logger.warning(f"Member import failed: {result.message}")

        return result

    except ForbiddenException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Member import failed: {e}", exc_info=True)
        raise


@course_member_import_router.post(
    "/parse/{course_id}",
    response_model=CourseMemberImportParseResponse,
)
async def parse_member_file(
    course_id: str,
    request: CourseMemberImportFileParseRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)] = None,
    db: Session = Depends(get_db),
) -> CourseMemberImportParseResponse:
    """Parse an uploaded member file (CSV/JSON/XLSX/Excel-XML) into preview rows.

    Read-only: it never touches the database. The client shows the rows for
    review/edit and then imports selected ones via ``POST /course-member-import/{id}``.

    **Required Permissions**: Lecturer role or higher (admins and organization
    managers may parse for any course).
    """
    # Same authorization as the single-member import.
    if permissions.is_admin or "_organization_manager" in permissions.roles:
        course = db.query(Course).filter(Course.id == course_id).first()
    else:
        course = check_course_permissions(permissions, Course, "_lecturer", db).filter(
            Course.id == course_id
        ).first()
    if not course:
        raise ForbiddenException(
            detail="You don't have permission to import course members. "
            "Lecturer role or higher is required."
        )

    try:
        data = base64.b64decode(request.content_base64, validate=True)
    except Exception:
        raise BadRequestException(detail="Invalid base64 file content.")

    try:
        rows, detected_format = parse_course_member_file(request.filename, data)
    except ValueError as e:
        raise BadRequestException(detail=str(e))

    return CourseMemberImportParseResponse(rows=rows, detected_format=detected_format)
