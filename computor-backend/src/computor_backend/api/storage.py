import io
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from computor_backend.permissions.principal import Principal
from computor_types.storage import (
    StorageObjectCreate,
    StorageObjectGet,
    StorageObjectList,
    StorageObjectUpdate,
    StorageObjectQuery,
    StorageObjectMetadata,
    BucketCreate,
    BucketInfo,
    BucketList,
    PresignedUrlRequest,
    PresignedUrlResponse,
    StorageUsageStats,
    StorageInterface
)
from ..services.storage_service import get_storage_service
from ..permissions.auth import get_current_principal
from ..api.exceptions import BadRequestException, NotFoundException, ForbiddenException
from ..redis_cache import get_redis_client
from ..storage_security import sanitize_filename, perform_full_file_validation
from ..storage_config import format_bytes

logger = logging.getLogger(__name__)

storage_router = APIRouter(prefix="/storage", tags=["storage"])

@storage_router.post("/upload", response_model=StorageObjectGet)
async def upload_file(
    file: UploadFile = File(...),
    object_key: Optional[str] = Form(None),
    bucket_name: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
    storage_service = Depends(get_storage_service)
):
    """Upload a file to storage with security validation"""
    # Check permissions
    if not permissions.permitted("storage", "create"):
        raise ForbiddenException("You don't have permission to upload files")
    
    # Read file content once for validation
    file_content = await file.read()
    file_size = len(file_content)
    
    # Perform comprehensive file validation
    file_data = io.BytesIO(file_content)
    perform_full_file_validation(
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        file_data=file_data
    )
    
    # Sanitize filename
    safe_filename = sanitize_filename(file.filename)
    
    # Use sanitized filename as object key if not provided
    if not object_key:
        object_key = f"uploads/{permissions.user_id}/{safe_filename}"
    else:
        # Sanitize the provided object key
        object_key = object_key.replace('..', '').lstrip('/')
    
    # Parse metadata if provided
    custom_metadata = None
    if metadata:
        try:
            import json
            custom_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise BadRequestException("Invalid metadata format. Must be valid JSON")
    
    # Add security metadata
    if custom_metadata is None:
        custom_metadata = {}
    custom_metadata.update({
        'original_filename': file.filename,
        'uploaded_by': permissions.user_id,
        'content_type': file.content_type,
        'file_size': str(file_size)
    })
    
    # Reset file data position for upload
    file_data.seek(0)
    
    # Upload file
    logger.info(f"Uploading file: {object_key} ({format_bytes(file_size)})")
    storage_metadata = await storage_service.upload_file(
        file_data=file_data,
        object_key=object_key,
        bucket_name=bucket_name,
        content_type=file.content_type,
        metadata=custom_metadata
    )
    
    # Create response
    return StorageObjectGet(
        id=0,  # Would be from database in production
        object_key=object_key,
        bucket_name=bucket_name or storage_service.default_bucket,
        content_type=storage_metadata.content_type,
        size=storage_metadata.size,
        etag=storage_metadata.etag,
        last_modified=storage_metadata.last_modified,
        metadata=storage_metadata.metadata,
        created_by=permissions.user_id,
        updated_by=permissions.user_id
    )

@storage_router.get(
    "/download/{object_key:path}",
    responses={200: {"content": {"application/octet-stream": {}}}},
)
async def download_file(
    object_key: str,
    bucket_name: Optional[str] = Query(None),
    permissions: Principal = Depends(get_current_principal),
    storage_service = Depends(get_storage_service)
):
    """Download a file from storage"""
    # Check permissions
    if not permissions.permitted("storage", "get"):
        raise ForbiddenException("You don't have permission to download files")
    
    # Get file stream and metadata
    file_stream, metadata = await storage_service.get_file_stream(
        object_key=object_key,
        bucket_name=bucket_name
    )
    
    # Return streaming response
    return StreamingResponse(
        file_stream,
        media_type=metadata.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{object_key.split("/")[-1]}"',
            "Content-Length": str(metadata.size),
            "ETag": metadata.etag
        }
    )

@storage_router.get("/objects", response_model=List[StorageObjectList])
async def list_objects(
    query: StorageObjectQuery = Depends(),
    permissions: Principal = Depends(get_current_principal),
    storage_service = Depends(get_storage_service),
    redis_client = Depends(get_redis_client)
):
    """List objects in storage with optional filtering"""
    # Check permissions
    if not permissions.permitted("storage","list"):
        raise ForbiddenException("You don't have permission to list files")
    
    # Check cache
    cache_key = f"storage:list:{query.bucket_name}:{query.prefix}:{query.skip}:{query.limit}"
    cached_data_raw = await redis_client.get(cache_key)
    if cached_data_raw:
        cached_data = json.loads(cached_data_raw)
        return [StorageObjectList(**item) for item in cached_data]
    
    # List objects
    objects = await storage_service.list_objects(
        bucket_name=query.bucket_name,
        prefix=query.prefix,
        recursive=True
    )
    
    # Filter and paginate
    result = []
    for obj in objects:
        # Apply filters
        if query.content_type and obj.content_type != query.content_type:
            continue
        if query.min_size and obj.size < query.min_size:
            continue
        if query.max_size and obj.size > query.max_size:
            continue
        
        result.append(StorageObjectList(
            id=0,  # Would be from database in production
            object_key=obj.object_name,
            bucket_name=obj.bucket_name,
            content_type=obj.content_type or "application/octet-stream",
            size=obj.size,
            last_modified=obj.last_modified
        ))
    
    # Apply pagination
    paginated_result = result[query.skip:query.skip + query.limit]
    
    # Cache result (convert to dict for JSON serialization)
    cache_data = [obj.model_dump(mode='json') for obj in paginated_result]
    await redis_client.set(cache_key, json.dumps(cache_data), ex=StorageInterface.cache_ttl)
    
    return paginated_result

@storage_router.get("/objects/{object_key:path}", response_model=StorageObjectGet)
async def get_object_info(
    object_key: str,
    bucket_name: Optional[str] = Query(None),
    permissions: Principal = Depends(get_current_principal),
    storage_service = Depends(get_storage_service)
):
    """Get metadata for a specific object"""
    # Check permissions
    if not permissions.permitted("storage", "get"):
        raise ForbiddenException("You don't have permission to view file info")
    
    # Get object metadata
    metadata = await storage_service.get_object_info(
        object_key=object_key,
        bucket_name=bucket_name
    )
    
    # Generate presigned URL for download
    presigned = await storage_service.generate_presigned_url(
        object_key=object_key,
        bucket_name=bucket_name,
        method="GET",
        expiry_seconds=3600
    )
    
    return StorageObjectGet(
        id=0,  # Would be from database in production
        object_key=object_key,
        bucket_name=bucket_name or storage_service.default_bucket,
        content_type=metadata.content_type,
        size=metadata.size,
        etag=metadata.etag,
        last_modified=metadata.last_modified,
        metadata=metadata.metadata,
        download_url=presigned.url
    )

@storage_router.delete("/objects/{object_key:path}")
async def delete_object(
    object_key: str,
    bucket_name: Optional[str] = Query(None),
    permissions: Principal = Depends(get_current_principal),
    storage_service = Depends(get_storage_service),
    redis_client = Depends(get_redis_client)
):
    """Delete an object from storage"""
    # Check permissions
    if not permissions.permitted("storage", "delete"):
        raise ForbiddenException("You don't have permission to delete files")
    
    # Delete object
    success = await storage_service.delete_file(
        object_key=object_key,
        bucket_name=bucket_name
    )
    
    # Clear cache
    cache_pattern = f"storage:*"
    keys = await redis_client.keys(cache_pattern)
    if keys:
        await redis_client.delete(*keys)
    
    return {"success": success, "message": f"Object {object_key} deleted successfully"}

@storage_router.post("/copy")
async def copy_object(
    source_object: str = Form(...),
    dest_object: str = Form(...),
    source_bucket: Optional[str] = Form(None),
    dest_bucket: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    permissions: Principal = Depends(get_current_principal),
    storage_service = Depends(get_storage_service)
):
    """Copy an object within or between buckets"""
    # Check permissions
    if not permissions.permitted("storage", "create"):
        raise ForbiddenException("You don't have permission to copy files")
    
    # Parse metadata if provided
    custom_metadata = None
    if metadata:
        try:
            custom_metadata = eval(metadata)  # Simple parsing for demo, use json.loads in production
        except:
            raise BadRequestException("Invalid metadata format")
    
    # Copy object
    result = await storage_service.copy_object(
        source_object=source_object,
        dest_object=dest_object,
        source_bucket=source_bucket,
        dest_bucket=dest_bucket,
        metadata=custom_metadata
    )
    
    return {
        "success": True,
        "message": f"Object copied successfully",
        "metadata": result.model_dump()
    }

@storage_router.post("/presigned-url", response_model=PresignedUrlResponse)
async def generate_presigned_url(
    request: PresignedUrlRequest,
    permissions: Principal = Depends(get_current_principal),
    storage_service = Depends(get_storage_service)
):
    """Generate a presigned URL for direct object access"""
    # Check permissions based on method
    if request.method == "GET" and not permissions.permitted("storage", "get"):
        raise ForbiddenException("You don't have permission to generate download URLs")
    elif request.method in ["PUT", "POST"] and not permissions.permitted("storage", "create"):
        raise ForbiddenException("You don't have permission to generate upload URLs")
    elif request.method == "DELETE" and not permissions.permitted("storage", "delete"):
        raise ForbiddenException("You don't have permission to generate delete URLs")
    
    # Generate presigned URL
    return await storage_service.generate_presigned_url(
        object_key=request.object_key,
        bucket_name=request.bucket_name,
        method=request.method,
        expiry_seconds=request.expiry_seconds
    )

# Bucket management endpoints

@storage_router.get("/buckets", response_model=List[BucketInfo])
async def list_buckets(
    permissions: Principal = Depends(get_current_principal),
    storage_service = Depends(get_storage_service)
):
    """List all available buckets"""
    # Check permissions
    if not permissions.permitted("storage", "admin"):
        raise ForbiddenException("You don't have permission to list buckets")
    
    return await storage_service.list_buckets()

@storage_router.post("/buckets", response_model=BucketInfo)
async def create_bucket(
    bucket: BucketCreate,
    permissions: Principal = Depends(get_current_principal),
    storage_service = Depends(get_storage_service)
):
    """Create a new storage bucket"""
    # Check permissions
    if not permissions.permitted("storage", "admin"):
        raise ForbiddenException("You don't have permission to create buckets")
    
    return await storage_service.create_bucket(
        bucket_name=bucket.bucket_name,
        region=bucket.region
    )

@storage_router.delete("/buckets/{bucket_name}")
async def delete_bucket(
    bucket_name: str,
    force: bool = Query(False, description="Force delete even if bucket is not empty"),
    permissions: Principal = Depends(get_current_principal),
    storage_service = Depends(get_storage_service)
):
    """Delete a storage bucket"""
    # Check permissions
    if not permissions.permitted("storage", "admin"):
        raise ForbiddenException("You don't have permission to delete buckets")
    
    success = await storage_service.delete_bucket(bucket_name, force=force)
    
    return {"success": success, "message": f"Bucket {bucket_name} deleted successfully"}

@storage_router.get("/buckets/{bucket_name}/stats", response_model=StorageUsageStats)
async def get_bucket_stats(
    bucket_name: str,
    permissions: Principal = Depends(get_current_principal),
    storage_service = Depends(get_storage_service),
    redis_client = Depends(get_redis_client)
):
    """Get usage statistics for a bucket"""
    # Check permissions
    if not permissions.permitted("storage", "get"):
        raise ForbiddenException("You don't have permission to view bucket statistics")
    
    # Check cache
    cache_key = f"storage:stats:{bucket_name}"
    cached_result_raw = await redis_client.get(cache_key)
    if cached_result_raw:
        cached_result = json.loads(cached_result_raw)
        return StorageUsageStats(**cached_result)

    # Get stats
    stats = await storage_service.get_bucket_stats(bucket_name)

    # Cache result (convert to dict for JSON serialization)
    await redis_client.set(cache_key, json.dumps(stats.model_dump(mode='json')), ex=300)  # Cache for 5 minutes
    
    return stats
