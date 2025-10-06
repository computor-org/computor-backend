from typing import Annotated
from uuid import UUID
from fastapi import Depends
from sqlalchemy.orm import Session

from computor_backend.api.filesystem import mirror_entity_to_filesystem
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.database import get_db
from computor_types.course_execution_backends import CourseExecutionBackendGet
from computor_types.courses import CourseGet
from computor_backend.api.api_builder import CrudRouter
from computor_backend.interfaces import CourseInterface

# Import business logic
from computor_backend.business_logic.courses import (
    update_course_execution_backend,
    delete_course_execution_backend,
)

course_router = CrudRouter(CourseInterface)

@course_router.router.patch("/{course_id}/execution-backends/{execution_backend_id}", response_model=CourseExecutionBackendGet)
async def patch_course_execution_backend_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    course_id: UUID | str,
    execution_backend_id: UUID | str,
    entity: dict,
    db: Session = Depends(get_db)
):
    """Update course execution backend configuration."""
    return await update_course_execution_backend(
        course_id=course_id,
        execution_backend_id=execution_backend_id,
        entity=entity,
        permissions=permissions,
        db=db,
    )

@course_router.router.delete("/{course_id}/execution-backends/{execution_backend_id}", response_model=dict)
def delete_course_execution_backend_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    course_id: UUID | str,
    execution_backend_id: UUID | str,
    db: Session = Depends(get_db)
):
    """Delete course execution backend."""
    return delete_course_execution_backend(
        course_id=course_id,
        execution_backend_id=execution_backend_id,
        permissions=permissions,
        db=db,
    )

async def event_wrapper(entity: CourseGet, db: Session, permissions: Principal):
    try:
        await mirror_entity_to_filesystem(str(entity.id),CourseInterface,db)

    except Exception as e:
        print(e)

course_router.on_created.append(event_wrapper)
course_router.on_updated.append(event_wrapper)