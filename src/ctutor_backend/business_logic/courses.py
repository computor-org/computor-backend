"""Business logic for course management."""
import logging
from uuid import UUID
from sqlalchemy import and_
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ctutor_backend.api.exceptions import BadRequestException, InternalServerException, NotFoundException
from ctutor_backend.business_logic.crud import update_entity as update_db
from ctutor_backend.permissions.core import check_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.interface.course_execution_backends import (
    CourseExecutionBackendGet,
    CourseExecutionBackendUpdate,
)
from ctutor_backend.model.course import CourseExecutionBackend

logger = logging.getLogger(__name__)


async def update_course_execution_backend(
    course_id: UUID | str,
    execution_backend_id: UUID | str,
    entity: dict,
    permissions: Principal,
    db: Session,
) -> CourseExecutionBackendGet:
    """Update a course execution backend configuration."""

    # Wrap blocking query in threadpool
    def _find_entity():
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

        if not entity_model:
            raise NotFoundException("Course execution backend not found")

        return entity_model

    entity_model = await run_in_threadpool(_find_entity)

    # Use the entity's id for the update
    return await update_db(
        permissions,
        db,
        entity_model.id,
        entity,
        CourseExecutionBackend,
        CourseExecutionBackendGet
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
