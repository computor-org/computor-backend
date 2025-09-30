from typing import Annotated
from uuid import UUID
from fastapi import Depends
from sqlalchemy import exc
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ctutor_backend.api.exceptions import BadRequestException, InternalServerException, NotFoundException
from ctutor_backend.api.crud import update_db
from ctutor_backend.api.filesystem import mirror_entity_to_filesystem
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.core import check_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.database import get_db
from ctutor_backend.interface.course_execution_backends import CourseExecutionBackendGet, CourseExecutionBackendUpdate
from ctutor_backend.api.api_builder import CrudRouter
from ctutor_backend.model.course import CourseExecutionBackend
from ctutor_backend.interface.courses import CourseGet, CourseInterface
course_router = CrudRouter(CourseInterface)

@course_router.router.patch("/{course_id}/execution-backends/{execution_backend_id}", response_model=CourseExecutionBackendGet)
def patch_course_execution_backend(permissions: Annotated[Principal, Depends(get_current_principal)], course_id: UUID | str, execution_backend_id: UUID | str, entity: dict, db: Session = Depends(get_db)):

    query = check_permissions(permissions,CourseExecutionBackend,"update",db)

    try:
        entity_model = query.filter(
            and_(CourseExecutionBackend.course_id == course_id, CourseExecutionBackend.execution_backend_id == execution_backend_id)).first()
    except:
        raise BadRequestException()
    
    return update_db(db, None, entity, CourseExecutionBackend, CourseExecutionBackendUpdate, CourseExecutionBackendGet, entity_model)

@course_router.router.delete("/{course_id}/execution-backends/{execution_backend_id}", response_model=dict)
def delete_course_execution_backend(permissions: Annotated[Principal, Depends(get_current_principal)], course_id: UUID | str, execution_backend_id: UUID | str, db: Session = Depends(get_db)):

    query = check_permissions(permissions,CourseExecutionBackend,"delete",db)

    entity = query.filter(
        and_(CourseExecutionBackend.course_id == course_id, CourseExecutionBackend.execution_backend_id == execution_backend_id)).first()

    if not entity:
        raise NotFoundException(detail=f"{CourseExecutionBackend.__name__} not found")

    try:
        db.delete(entity)
        db.commit()
    except exc.SQLAlchemyError as e:
        # TODO: proper error handling
        raise InternalServerException(detail=e.args)
    except Exception as e:
        raise InternalServerException(detail=e.args)

    return {"ok": True}

async def event_wrapper(entity: CourseGet, db: Session, permissions: Principal):
    try:
        await mirror_entity_to_filesystem(str(entity.id),CourseInterface,db)

    except Exception as e:
        print(e)

course_router.on_created.append(event_wrapper)
course_router.on_updated.append(event_wrapper)