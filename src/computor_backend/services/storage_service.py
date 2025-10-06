import logging
from datetime import datetime, timedelta, timezone
from typing import BinaryIO, Optional, Dict, List, Tuple
from minio.error import S3Error
from minio.datatypes import Object
from minio.commonconfig import CopySource

from ..minio_client import get_minio_client, MINIO_DEFAULT_BUCKET
from ..api.exceptions import (
    ServiceUnavailableException, 
    NotFoundException, 
    BadRequestException
)
from computor_types.storage import (
    StorageObjectMetadata,
    BucketInfo,
    PresignedUrlResponse,
    StorageUsageStats
)

logger = logging.getLogger(__name__)


class StorageService:
    """Service for handling MinIO storage operations"""
    
    def __init__(self):
        self.client = get_minio_client()
        self.default_bucket = MINIO_DEFAULT_BUCKET
    
    async def ensure_bucket_exists(self, bucket_name: Optional[str] = None) -> str:
        """Ensure bucket exists, create if it doesn't"""
        bucket = bucket_name or self.default_bucket
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info(f"Created bucket: {bucket}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise ServiceUnavailableException(f"Storage service error: {e}")
        return bucket
    
    async def upload_file(
        self, 
        file_data: BinaryIO, 
        object_key: str,
        bucket_name: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageObjectMetadata:
        """Upload a file to MinIO storage"""
        bucket = await self.ensure_bucket_exists(bucket_name)
        
        try:
            # Get file size
            file_data.seek(0, 2)  # Seek to end
            file_size = file_data.tell()
            file_data.seek(0)  # Seek back to start
            
            # Prepare metadata
            if metadata:
                # MinIO metadata keys must be prefixed with 'x-amz-meta-'
                minio_metadata = {f"x-amz-meta-{k}": v for k, v in metadata.items()}
            else:
                minio_metadata = {}
            
            # Upload file
            self.client.put_object(
                bucket_name=bucket,
                object_name=object_key,
                data=file_data,
                length=file_size,
                content_type=content_type or 'application/octet-stream',
                metadata=minio_metadata
            )
            
            logger.info(f"Uploaded object: {bucket}/{object_key}")
            
            # Get object info for response
            stat = self.client.stat_object(bucket, object_key)
            
            return StorageObjectMetadata(
                content_type=stat.content_type,
                size=stat.size,
                etag=stat.etag,
                last_modified=stat.last_modified,
                metadata=self._extract_custom_metadata(stat.metadata)
            )
            
        except S3Error as e:
            logger.error(f"Error uploading file: {e}")
            if e.code == 'NoSuchBucket':
                raise NotFoundException(f"Bucket not found: {bucket}")
            raise ServiceUnavailableException(f"Storage upload error: {e}")
    
    async def download_file(
        self, 
        object_key: str,
        bucket_name: Optional[str] = None
    ) -> bytes:
        """Download a file from MinIO storage"""
        bucket = bucket_name or self.default_bucket
        
        try:
            response = self.client.get_object(bucket, object_key)
            data = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"Downloaded object: {bucket}/{object_key}")
            return data
            
        except S3Error as e:
            logger.error(f"Error downloading file: {e}")
            if e.code == 'NoSuchKey':
                raise NotFoundException(f"Object not found: {object_key}")
            if e.code == 'NoSuchBucket':
                raise NotFoundException(f"Bucket not found: {bucket}")
            raise ServiceUnavailableException(f"Storage download error: {e}")
    
    async def get_file_stream(
        self, 
        object_key: str,
        bucket_name: Optional[str] = None
    ) -> Tuple[BinaryIO, StorageObjectMetadata]:
        """Get a file stream from MinIO storage"""
        bucket = bucket_name or self.default_bucket
        
        try:
            response = self.client.get_object(bucket, object_key)
            
            # Get object metadata
            stat = self.client.stat_object(bucket, object_key)
            metadata = StorageObjectMetadata(
                content_type=stat.content_type,
                size=stat.size,
                etag=stat.etag,
                last_modified=stat.last_modified,
                metadata=self._extract_custom_metadata(stat.metadata)
            )
            
            return response, metadata
            
        except S3Error as e:
            logger.error(f"Error getting file stream: {e}")
            if e.code == 'NoSuchKey':
                raise NotFoundException(f"Object not found: {object_key}")
            if e.code == 'NoSuchBucket':
                raise NotFoundException(f"Bucket not found: {bucket}")
            raise ServiceUnavailableException(f"Storage stream error: {e}")
    
    async def delete_file(
        self, 
        object_key: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """Delete a file from MinIO storage"""
        bucket = bucket_name or self.default_bucket
        
        try:
            self.client.remove_object(bucket, object_key)
            logger.info(f"Deleted object: {bucket}/{object_key}")
            return True
            
        except S3Error as e:
            logger.error(f"Error deleting file: {e}")
            if e.code == 'NoSuchKey':
                raise NotFoundException(f"Object not found: {object_key}")
            if e.code == 'NoSuchBucket':
                raise NotFoundException(f"Bucket not found: {bucket}")
            raise ServiceUnavailableException(f"Storage delete error: {e}")
    
    async def list_objects(
        self,
        bucket_name: Optional[str] = None,
        prefix: Optional[str] = None,
        recursive: bool = True,
        include_user_metadata: bool = False
    ) -> List[Object]:
        """List objects in a bucket with optional prefix"""
        bucket = bucket_name or self.default_bucket
        
        try:
            objects = self.client.list_objects(
                bucket_name=bucket,
                prefix=prefix,
                recursive=recursive,
                include_user_meta=include_user_metadata
            )
            
            return list(objects)
            
        except S3Error as e:
            logger.error(f"Error listing objects: {e}")
            if e.code == 'NoSuchBucket':
                raise NotFoundException(f"Bucket not found: {bucket}")
            raise ServiceUnavailableException(f"Storage list error: {e}")
    
    async def get_object_info(
        self,
        object_key: str,
        bucket_name: Optional[str] = None
    ) -> StorageObjectMetadata:
        """Get metadata for a specific object"""
        bucket = bucket_name or self.default_bucket
        
        try:
            stat = self.client.stat_object(bucket, object_key)
            
            return StorageObjectMetadata(
                content_type=stat.content_type,
                size=stat.size,
                etag=stat.etag,
                last_modified=stat.last_modified,
                metadata=self._extract_custom_metadata(stat.metadata)
            )
            
        except S3Error as e:
            logger.error(f"Error getting object info: {e}")
            if e.code == 'NoSuchKey':
                raise NotFoundException(f"Object not found: {object_key}")
            if e.code == 'NoSuchBucket':
                raise NotFoundException(f"Bucket not found: {bucket}")
            raise ServiceUnavailableException(f"Storage info error: {e}")
    
    async def copy_object(
        self,
        source_object: str,
        dest_object: str,
        source_bucket: Optional[str] = None,
        dest_bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageObjectMetadata:
        """Copy an object within or between buckets"""
        src_bucket = source_bucket or self.default_bucket
        dst_bucket = await self.ensure_bucket_exists(dest_bucket)
        
        try:
            # Prepare copy source
            copy_source = CopySource(src_bucket, source_object)
            
            # Prepare metadata
            if metadata:
                minio_metadata = {f"x-amz-meta-{k}": v for k, v in metadata.items()}
            else:
                minio_metadata = None
            
            # Copy object
            self.client.copy_object(
                bucket_name=dst_bucket,
                object_name=dest_object,
                source=copy_source,
                metadata=minio_metadata
            )
            
            logger.info(f"Copied object: {copy_source} -> {dst_bucket}/{dest_object}")
            
            # Get object info for response
            stat = self.client.stat_object(dst_bucket, dest_object)
            
            return StorageObjectMetadata(
                content_type=stat.content_type,
                size=stat.size,
                etag=stat.etag,
                last_modified=stat.last_modified,
                metadata=self._extract_custom_metadata(stat.metadata)
            )
            
        except S3Error as e:
            logger.error(f"Error copying object: {e}")
            if e.code == 'NoSuchKey':
                raise NotFoundException(f"Source object not found: {source_object}")
            if e.code == 'NoSuchBucket':
                raise NotFoundException(f"Bucket not found")
            raise ServiceUnavailableException(f"Storage copy error: {e}")
    
    async def generate_presigned_url(
        self,
        object_key: str,
        bucket_name: Optional[str] = None,
        method: str = "GET",
        expiry_seconds: int = 3600
    ) -> PresignedUrlResponse:
        """Generate a presigned URL for object access"""
        bucket = bucket_name or self.default_bucket
        
        try:
            if method.upper() == "GET":
                url = self.client.presigned_get_object(
                    bucket_name=bucket,
                    object_name=object_key,
                    expires=timedelta(seconds=expiry_seconds)
                )
            elif method.upper() == "PUT":
                url = self.client.presigned_put_object(
                    bucket_name=bucket,
                    object_name=object_key,
                    expires=timedelta(seconds=expiry_seconds)
                )
            else:
                raise BadRequestException(f"Unsupported method for presigned URL: {method}")
            
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expiry_seconds)
            
            return PresignedUrlResponse(
                url=url,
                expires_at=expires_at,
                method=method.upper()
            )
            
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise ServiceUnavailableException(f"Presigned URL error: {e}")
    
    async def list_buckets(self) -> List[BucketInfo]:
        """List all buckets"""
        try:
            buckets = self.client.list_buckets()
            
            return [
                BucketInfo(
                    bucket_name=bucket.name,
                    creation_date=bucket.creation_date
                )
                for bucket in buckets
            ]
            
        except S3Error as e:
            logger.error(f"Error listing buckets: {e}")
            raise ServiceUnavailableException(f"Bucket list error: {e}")
    
    async def create_bucket(self, bucket_name: str, region: Optional[str] = None) -> BucketInfo:
        """Create a new bucket"""
        try:
            if self.client.bucket_exists(bucket_name):
                raise BadRequestException(f"Bucket already exists: {bucket_name}")
            
            self.client.make_bucket(bucket_name, location=region)
            logger.info(f"Created bucket: {bucket_name}")
            
            return BucketInfo(
                bucket_name=bucket_name,
                creation_date=datetime.now(timezone.utc),
                region=region
            )
            
        except S3Error as e:
            logger.error(f"Error creating bucket: {e}")
            raise ServiceUnavailableException(f"Bucket creation error: {e}")
    
    async def delete_bucket(self, bucket_name: str, force: bool = False) -> bool:
        """Delete a bucket"""
        try:
            if force:
                # Remove all objects in the bucket first
                objects = self.client.list_objects(bucket_name, recursive=True)
                for obj in objects:
                    self.client.remove_object(bucket_name, obj.object_name)
                    logger.info(f"Deleted object: {bucket_name}/{obj.object_name}")
            
            self.client.remove_bucket(bucket_name)
            logger.info(f"Deleted bucket: {bucket_name}")
            return True
            
        except S3Error as e:
            logger.error(f"Error deleting bucket: {e}")
            if e.code == 'NoSuchBucket':
                raise NotFoundException(f"Bucket not found: {bucket_name}")
            if e.code == 'BucketNotEmpty':
                raise BadRequestException(f"Bucket not empty: {bucket_name}. Use force=true to delete all objects.")
            raise ServiceUnavailableException(f"Bucket deletion error: {e}")
    
    async def get_bucket_stats(self, bucket_name: Optional[str] = None) -> StorageUsageStats:
        """Get storage usage statistics for a bucket"""
        bucket = bucket_name or self.default_bucket
        
        try:
            objects = self.client.list_objects(bucket, recursive=True)
            
            total_size = 0
            object_count = 0
            
            for obj in objects:
                total_size += obj.size
                object_count += 1
            
            return StorageUsageStats(
                bucket_name=bucket,
                object_count=object_count,
                total_size=total_size,
                last_updated=datetime.now(timezone.utc)
            )
            
        except S3Error as e:
            logger.error(f"Error getting bucket stats: {e}")
            if e.code == 'NoSuchBucket':
                raise NotFoundException(f"Bucket not found: {bucket}")
            raise ServiceUnavailableException(f"Bucket stats error: {e}")
    
    def _extract_custom_metadata(self, metadata: Dict[str, str]) -> Dict[str, str]:
        """Extract custom metadata from MinIO metadata"""
        custom_metadata = {}
        for key, value in metadata.items():
            if key.startswith('X-Amz-Meta-'):
                # Remove the prefix and convert to lowercase
                custom_key = key[11:].lower()
                custom_metadata[custom_key] = value
        return custom_metadata


# Singleton instance getter
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get the singleton storage service instance"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service