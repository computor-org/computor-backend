"""Business logic for course management."""
import logging
from uuid import UUID
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ctutor_backend.api.exceptions import BadRequestException, InternalServerException, NotFoundException
from ctutor_backend.api.crud import update_db
from ctutor_backend.permissions.core import check_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.interface.course_execution_backends import (
    CourseExecutionBackendGet,
    CourseExecutionBackendUpdate,
)
from ctutor_backend.model.course import CourseExecutionBackend

logger = logging.getLogger(__name__)


def update_course_execution_backend(
    course_id: UUID | str,
    execution_backend_id: UUID | str,
    entity: dict,
    permissions: Principal,
    db: Session,
) -> CourseExecutionBackendGet:
    """Update a course execution backend configuration."""

    query = check_permissions(permissions, CourseExecutionBackend, "update", db)

    try:
        entity_model = query.filter(
            and_(
                CourseExecutionBackend.course_id == course_id,
                CourseExecutionBackend.execution_backend_id == execution_backend_id
            )
        ).first()
    except Exception:
        raise BadRequestException()

    return update_db(
        db,
        None,
        entity,
        CourseExecutionBackend,
        CourseExecutionBackendUpdate,
        CourseExecutionBackendGet,
        entity_model
    )


def delete_course_execution_backend(
    course_id: UUID | str,
    execution_backend_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> dict:
    """Delete a course execution backend."""

    query = check_permissions(permissions, CourseExecutionBackend, "delete", db)

    entity = query.filter(
        and_(
            CourseExecutionBackend.course_id == course_id,
            CourseExecutionBackend.execution_backend_id == execution_backend_id
        )
    ).first()

    if not entity:
        raise NotFoundException(detail=f"{CourseExecutionBackend.__name__} not found")

    try:
        db.delete(entity)
        db.commit()
    except Exception as e:
        logger.error(f"Error deleting course execution backend: {e}")
        raise InternalServerException(detail=str(e))

    return {"ok": True}
