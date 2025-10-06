from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from computor_backend.business_logic.crud import (
    create_entity as create_db,
    delete_entity as delete_db,
    get_entity_by_id as get_id_db,
    list_entities as list_db,
    update_entity as update_db
)
from computor_backend.database import get_db
from computor_types.results import (
    ResultCreate,
    ResultGet,
    ResultInterface,
    ResultList,
    ResultUpdate,
    ResultQuery,
)
from computor_types.tasks import TaskStatus
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal

# Import business logic
from computor_backend.business_logic.results import get_result_status

result_router = APIRouter(prefix="/results", tags=["results"])


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
    return await update_db(
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
    await delete_db(permissions, db, result_id, ResultInterface.model)


@result_router.get("/{result_id}/status", response_model=TaskStatus)
async def result_status(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    result_id: UUID | str,
    db: Session = Depends(get_db),
):
    """Get the current status of a test result."""
    return await get_result_status(result_id, permissions, db)
