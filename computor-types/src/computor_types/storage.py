from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, field_validator
from .base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery

class StorageObjectMetadata(BaseModel):
    """Metadata for storage objects"""
    content_type: str = Field(..., description="MIME type of the object")
    size: int = Field(..., description="Size of the object in bytes")
    etag: str = Field(..., description="Entity tag of the object")
    last_modified: datetime = Field(..., description="Last modification timestamp")
    metadata: Optional[Dict[str, str]] = Field(None, description="Custom metadata")

class StorageObjectCreate(BaseModel):
    """DTO for creating/uploading a storage object"""
    object_key: str = Field(..., description="Key/path for the object in the bucket")
    bucket_name: Optional[str] = Field(None, description="Target bucket name")
    metadata: Optional[Dict[str, str]] = Field(None, description="Custom metadata for the object")
    content_type: Optional[str] = Field(None, description="MIME type of the object")
    
    @field_validator('object_key')
    def validate_object_key(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("Object key cannot be empty")
        # Remove leading slashes
        return v.lstrip('/')

class StorageObjectGet(BaseEntityGet, StorageObjectMetadata):
    """DTO for retrieving a storage object"""
    id: int = Field(..., description="Storage object ID")
    object_key: str = Field(..., description="Object key/path in the bucket")
    bucket_name: str = Field(..., description="Bucket name")
    download_url: Optional[str] = Field(None, description="Presigned download URL")
    

class StorageObjectList(BaseEntityList):
    """DTO for listing storage objects"""
    id: int = Field(..., description="Storage object ID")
    object_key: str = Field(..., description="Object key/path in the bucket")
    bucket_name: str = Field(..., description="Bucket name")
    content_type: str = Field(..., description="MIME type of the object")
    size: int = Field(..., description="Size of the object in bytes")
    last_modified: datetime = Field(..., description="Last modification timestamp")

class StorageObjectUpdate(BaseModel):
    """DTO for updating storage object metadata"""
    metadata: Optional[Dict[str, str]] = Field(None, description="Updated custom metadata")
    content_type: Optional[str] = Field(None, description="Updated MIME type")

class StorageObjectQuery(ListQuery):
    """Query parameters for filtering storage objects"""
    bucket_name: Optional[str] = Field(None, description="Filter by bucket name")
    prefix: Optional[str] = Field(None, description="Filter by object key prefix")
    content_type: Optional[str] = Field(None, description="Filter by content type")
    min_size: Optional[int] = Field(None, description="Minimum object size in bytes")
    max_size: Optional[int] = Field(None, description="Maximum object size in bytes")
    
    @field_validator('prefix')
    def validate_prefix(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.lstrip('/')
        return v

class BucketCreate(BaseModel):
    """DTO for creating a storage bucket"""
    bucket_name: str = Field(..., description="Name of the bucket to create")
    region: Optional[str] = Field(None, description="Region for the bucket")
    
    @field_validator('bucket_name')
    def validate_bucket_name(cls, v: str) -> str:
        # MinIO bucket naming rules
        if not v or len(v) < 3 or len(v) > 63:
            raise ValueError("Bucket name must be between 3 and 63 characters")
        if not v.replace('-', '').replace('.', '').isalnum():
            raise ValueError("Bucket name can only contain letters, numbers, hyphens, and dots")
        if v.startswith('-') or v.endswith('-'):
            raise ValueError("Bucket name cannot start or end with a hyphen")
        return v.lower()

class BucketInfo(BaseModel):
    """DTO for bucket information"""
    bucket_name: str = Field(..., description="Name of the bucket")
    creation_date: Optional[datetime] = Field(None, description="Bucket creation date")
    region: Optional[str] = Field(None, description="Bucket region")

class BucketList(BaseModel):
    """DTO for listing buckets"""
    buckets: List[BucketInfo] = Field(..., description="List of buckets")

class PresignedUrlRequest(BaseModel):
    """DTO for generating presigned URLs"""
    object_key: str = Field(..., description="Object key/path in the bucket")
    bucket_name: Optional[str] = Field(None, description="Bucket name")
    expiry_seconds: Optional[int] = Field(3600, description="URL expiry time in seconds", ge=1, le=604800)  # Max 7 days
    method: Optional[str] = Field("GET", description="HTTP method for the presigned URL")
    
    @field_validator('method')
    def validate_method(cls, v: str) -> str:
        allowed_methods = ["GET", "PUT", "POST", "DELETE"]
        if v.upper() not in allowed_methods:
            raise ValueError(f"Method must be one of {allowed_methods}")
        return v.upper()

class PresignedUrlResponse(BaseModel):
    """DTO for presigned URL response"""
    url: str = Field(..., description="The presigned URL")
    expires_at: datetime = Field(..., description="URL expiration timestamp")
    method: str = Field(..., description="HTTP method for the URL")

class StorageUsageStats(BaseModel):
    """DTO for storage usage statistics"""
    bucket_name: str = Field(..., description="Bucket name")
    object_count: int = Field(..., description="Number of objects in the bucket")
    total_size: int = Field(..., description="Total size of all objects in bytes")
    last_updated: datetime = Field(..., description="Last statistics update timestamp")

class StorageInterface(EntityInterface):
    """Interface for storage operations"""
    create = StorageObjectCreate
    get = StorageObjectGet
    list = StorageObjectList
    update = StorageObjectUpdate
    query = StorageObjectQuery
    endpoint = "storage"
    cache_ttl = 60  # Cache for 1 minute given the dynamic nature of storage