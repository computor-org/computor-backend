from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Response, status
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
    from computor_backend.services.result_storage import retrieve_result_json, list_result_artifacts
    result_json = await retrieve_result_json(result_id)

    # Fetch artifact information
    artifacts = await list_result_artifacts(result_id)

    # Build result_artifacts list
    result_artifacts = [
        {
            "id": f"{result_id}_{artifact['filename']}",
            "filename": artifact['filename'],
            "content_type": artifact.get('content_type'),
            "file_size": artifact['size'],
            "created_at": artifact['last_modified'].isoformat() if artifact.get('last_modified') else None,
        }
        for artifact in artifacts
    ]

    # Add result_json and artifact info to the response
    result_dict = result.model_dump()
    result_dict['result_json'] = result_json
    result_dict['has_artifacts'] = len(artifacts) > 0
    result_dict['artifact_count'] = len(artifacts)
    result_dict['result_artifacts'] = result_artifacts

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


# ===============================
# Result Artifact Endpoints
# ===============================

from computor_types.artifacts import ResultArtifactListItem
from typing import List


@result_router.get("/{result_id}/artifacts", response_model=List[ResultArtifactListItem])
async def list_result_artifacts_endpoint(
    result_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> List[ResultArtifactListItem]:
    """
    List all artifacts associated with a result.

    Artifacts are files generated during test execution, such as:
    - Plots and figures
    - Generated reports
    - Debug output files
    """
    from computor_backend.api.exceptions import NotFoundException

    # Verify the user has access to this result
    result = await get_id_db(permissions, db, result_id, ResultInterface)
    if result is None:
        raise NotFoundException(detail="Result not found")

    # List artifacts from MinIO
    from computor_backend.services.result_storage import list_result_artifacts, RESULTS_BUCKET
    artifacts = await list_result_artifacts(result_id)

    # Convert to ResultArtifactListItem format
    return [
        ResultArtifactListItem(
            id=f"{result_id}_{artifact['filename']}",  # Synthetic ID
            result_id=str(result_id),
            content_type=artifact.get('content_type'),
            file_size=artifact['size'],
            bucket_name=RESULTS_BUCKET,
            object_key=artifact['object_key'],
            created_at=artifact['last_modified'],
            properties={"filename": artifact['filename']},
        )
        for artifact in artifacts
    ]


@result_router.get(
    "/{result_id}/artifacts/download",
    responses={200: {"content": {"application/zip": {}}}},
)
async def download_result_artifacts(
    result_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """
    Download all artifacts for a result as a ZIP file.

    Returns a ZIP archive containing all artifacts generated during test execution.
    """
    from fastapi.responses import StreamingResponse
    from computor_backend.api.exceptions import NotFoundException
    import zipfile
    from io import BytesIO

    # Verify the user has access to this result
    result = await get_id_db(permissions, db, result_id, ResultInterface)
    if result is None:
        raise NotFoundException(detail="Result not found")

    # List artifacts from MinIO
    from computor_backend.services.result_storage import list_result_artifacts, retrieve_result_artifact
    artifacts = await list_result_artifacts(result_id)

    if not artifacts:
        raise NotFoundException(detail="No artifacts found for this result")

    # Create ZIP file in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for artifact in artifacts:
            filename = artifact['filename']
            # Retrieve artifact content from MinIO
            content = await retrieve_result_artifact(result_id, filename)
            if content:
                zip_file.writestr(filename, content)

    zip_buffer.seek(0)

    # Generate filename for the download
    download_filename = f"result_{result_id}_artifacts.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{download_filename}"'
        }
    )


@result_router.post("/{result_id}/artifacts/upload", status_code=status.HTTP_201_CREATED)
async def upload_result_artifacts(
    result_id: UUID | str,
    file: Annotated[bytes, File()],
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """
    Upload artifacts as a ZIP archive.

    The ZIP file is extracted and each file is stored as an artifact in MinIO.
    Directory structure within the ZIP is preserved.

    This endpoint allows testing workers to upload artifacts via API
    instead of directly accessing MinIO.
    """
    import zipfile
    from io import BytesIO
    from computor_backend.api.exceptions import NotFoundException, BadRequestException
    from computor_backend.services.result_storage import store_result_artifact
    from computor_types.artifacts import ArtifactInfo, ResultArtifactUploadResponse

    # Verify the user has access to this result
    result = await get_id_db(permissions, db, result_id, ResultInterface)
    if result is None:
        raise NotFoundException(detail="Result not found")

    # Read and validate ZIP
    zip_buffer = BytesIO(file)

    if not zipfile.is_zipfile(zip_buffer):
        raise BadRequestException(detail="File must be a valid ZIP archive")

    # Security: Validate ZIP file to prevent ZIP bomb attacks
    zip_buffer.seek(0)
    with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
        # Check for reasonable limits
        MAX_FILES = 1000
        MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB total uncompressed

        file_infos = zip_file.infolist()
        if len(file_infos) > MAX_FILES:
            raise BadRequestException(
                detail=f"ZIP contains too many files ({len(file_infos)}). Maximum is {MAX_FILES}."
            )

        total_size = sum(info.file_size for info in file_infos if not info.is_dir())
        if total_size > MAX_TOTAL_SIZE:
            raise BadRequestException(
                detail=f"ZIP total uncompressed size ({total_size} bytes) exceeds maximum ({MAX_TOTAL_SIZE} bytes)."
            )

    # Extract and store each file
    artifacts = []
    zip_buffer.seek(0)
    with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
        for zip_info in zip_file.infolist():
            if zip_info.is_dir():
                continue  # Skip directories

            filename = zip_info.filename
            file_data = zip_file.read(filename)

            # Store via existing service
            storage_info = await store_result_artifact(
                result_id=result_id,
                filename=filename,
                file_data=file_data,
            )

            artifacts.append(ArtifactInfo(
                filename=filename,
                file_size=len(file_data),
                content_type=storage_info.get('content_type'),
            ))

    return ResultArtifactUploadResponse(
        result_id=str(result_id),
        artifacts_count=len(artifacts),
        artifacts=artifacts,
    )
