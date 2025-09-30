from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ctutor_backend.api.crud import create_db, delete_db, get_id_db, list_db, update_db
from ctutor_backend.api.exceptions import NotFoundException
from ctutor_backend.database import get_db
from ctutor_backend.interface.results import (
    ResultCreate,
    ResultGet,
    ResultInterface,
    ResultList,
    ResultUpdate,
    ResultQuery,
)
from ctutor_backend.interface.tasks import TaskStatus, map_int_to_task_status
from ctutor_backend.model.result import Result
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.core import check_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.tasks import get_task_executor


result_router = APIRouter(prefix="/results", tags=["results"])


async def get_result_status(result: Result) -> TaskStatus:
    """Fetch the latest task status for a result from the task executor."""
    if not result.test_system_id:
        return map_int_to_task_status(result.status)
    try:
        task_executor = get_task_executor()
        task_info = await task_executor.get_task_status(result.test_system_id)
        return task_info.status
    except Exception:
        return TaskStatus.FAILED


@result_router.get("", response_model=list[ResultList])
async def list_results(
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: ResultQuery = Depends(),
    db: Session = Depends(get_db),
) -> list[ResultList]:
    results, total = await list_db(permissions, db, params, ResultInterface)
    response.headers["X-Total-Count"] = str(total)
    return results


@result_router.get("/{result_id}", response_model=ResultGet)
async def get_result(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    result_id: UUID | str,
    db: Session = Depends(get_db),
) -> ResultGet:
    return await get_id_db(permissions, db, result_id, ResultInterface)


@result_router.post("", response_model=ResultGet, status_code=status.HTTP_201_CREATED)
async def create_result(
    payload: ResultCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> ResultGet:
    return await create_db(
        permissions,
        db,
        payload,
        ResultInterface.model,
        ResultGet,
        getattr(ResultInterface, "post_create", None),
    )


@result_router.patch("/{result_id}", response_model=ResultGet)
async def update_result(
    result_id: UUID | str,
    payload: ResultUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> ResultGet:
    return update_db(
        permissions,
        db,
        result_id,
        payload,
        ResultInterface.model,
        ResultGet,
        post_update=getattr(ResultInterface, "post_update", None),
    )


@result_router.delete("/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_result(
    result_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    delete_db(permissions, db, result_id, ResultInterface.model)


@result_router.get("/{result_id}/status", response_model=TaskStatus)
async def result_status(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    result_id: UUID | str,
    db: Session = Depends(get_db),
):
    result = (
        check_permissions(permissions, Result, "get", db)
        .filter(Result.id == result_id)
        .first()
    )
    if result is None:
        raise NotFoundException()
    return await get_result_status(result)
