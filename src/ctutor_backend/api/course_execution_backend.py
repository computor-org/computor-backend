from typing import Annotated
from fastapi import Depends, Response
from fastapi import APIRouter
from sqlalchemy.orm import Session

from ctutor_backend.api.crud import create_db, list_db
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.database import get_db
from ctutor_backend.model.course import CourseExecutionBackend
from ctutor_backend.interface.course_execution_backends import CourseExecutionBackendCreate, CourseExecutionBackendGet, CourseExecutionBackendInterface, CourseExecutionBackendList, CourseExecutionBackendQuery
course_execution_backend_router = APIRouter()

@course_execution_backend_router.post("", response_model=CourseExecutionBackendGet)
async def create_course_execution_backend(permissions: Annotated[Principal, Depends(get_current_principal)], entity: CourseExecutionBackendCreate, db: Session = Depends(get_db)):

    return await create_db(permissions, db, entity, CourseExecutionBackend, CourseExecutionBackendGet)

@course_execution_backend_router.get("", response_model=list[CourseExecutionBackendList])
async def list_course_execution_backend(permissions: Annotated[Principal, Depends(get_current_principal)], response: Response, params: CourseExecutionBackendQuery = Depends(), db: Session = Depends(get_db)):

    data, total = await list_db(permissions, db, params, CourseExecutionBackendInterface)
    response.headers["X-Total-Count"] = str(total)
    return data