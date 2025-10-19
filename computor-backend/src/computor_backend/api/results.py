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
from computor_backend.redis_cache import get_cache
from computor_backend.cache import Cache
from computor_types.results import (
    ResultCreate,
    ResultGet,
    ResultList,
    ResultUpdate,
    ResultQuery,
)
from computor_backend.interfaces.result import ResultInterface
from computor_types.tasks import TaskStatus
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.repositories.result import ResultRepository

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
    # Get the base result from database
    result = await get_id_db(permissions, db, result_id, ResultInterface)

    # Fetch result_json from MinIO
    from computor_backend.services.result_storage import retrieve_result_json
    result_json = await retrieve_result_json(result_id)

    # Add result_json to the response
    result_dict = result.model_dump()
    result_dict['result_json'] = result_json

    return ResultGet.model_validate(result_dict)

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
    cache: Cache = Depends(get_cache),
) -> ResultGet:
    """
    Update a result.

    CRITICAL: Uses ResultRepository for automatic cache invalidation of:
    - Student views (GET /students/course-contents)
    - Tutor views (GET /tutors/course-members/{id}/course-contents)
    - Lecturer views
    """
    # Initialize repository with cache for automatic invalidation
    result_repo = ResultRepository(db, cache)

    # Check permissions using the standard permission system
    from computor_backend.permissions.core import check_permissions
    from computor_backend.api.exceptions import NotFoundException

    query = check_permissions(permissions, ResultInterface.model, "update", db)
    if query is None:
        raise NotFoundException()

    db_result = query.filter(ResultInterface.model.id == result_id).first()
    if db_result is None:
        raise NotFoundException()

    # Convert payload to dict
    updates = payload.model_dump(exclude_unset=True)

    # Convert TaskStatus enum to integer for database storage
    if 'status' in updates and updates['status'] is not None:
        from computor_types.tasks import map_task_status_to_int
        updates['status'] = map_task_status_to_int(updates['status'])

    # Handle result_json separately - store in MinIO if provided
    result_json_update = updates.pop('result_json', None)
    if result_json_update is not None:
        from computor_backend.services.result_storage import store_result_json
        await store_result_json(result_id, result_json_update)

    # Use repository for cache-aware update (triggers invalidation)
    # Pass the entity directly to avoid re-querying
    result = result_repo.update_entity(db_result, updates)

    # Fetch result_json from MinIO for response
    from computor_backend.services.result_storage import retrieve_result_json
    result_json = await retrieve_result_json(result_id)

    # Build response with result_json
    result_dict = ResultGet.model_validate(result, from_attributes=True).model_dump()
    result_dict['result_json'] = result_json

    return ResultGet.model_validate(result_dict)

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
