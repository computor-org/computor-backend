"""Auto-generated client for /storage endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.storage import (
    BucketCreate,
    BucketInfo,
    PresignedUrlRequest,
    PresignedUrlResponse,
    StorageObjectGet,
    StorageObjectList,
    StorageUsageStats,
)

from computor_client.base import FileOperationClient


class StorageClient(FileOperationClient):
    """Client for /storage endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/storage",
        )

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_storage_bucket_by_bucket_name(id)

    async def post_storage_upload(self, ) -> StorageObjectGet:
        """Upload File"""
        data = await self._request("POST", "/upload")
        if data:
            return StorageObjectGet.model_validate(data)
        return data

    async def get_storage_download_by_object_key(self, object_key: str, bucket_name: Optional[str] = None) -> Dict[str, Any]:
        """Download File"""
        params = {k: v for k, v in locals().items() if k in ['bucket_name'] and v is not None}
        data = await self._request("GET", f"/download/{object_key}", params=params)
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def get_storage_objects(self, skip: Optional[str] = None, limit: Optional[str] = None, bucket_name: Optional[str] = None, prefix: Optional[str] = None, content_type: Optional[str] = None, min_size: Optional[str] = None, max_size: Optional[str] = None) -> List[StorageObjectList]:
        """List Objects"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'bucket_name', 'prefix', 'content_type', 'min_size', 'max_size'] and v is not None}
        data = await self._request("GET", "/objects", params=params)
        if isinstance(data, list):
            return [StorageObjectList.model_validate(item) for item in data]
        return data

    async def get_storage_object_by_object_key(self, object_key: str, bucket_name: Optional[str] = None) -> StorageObjectGet:
        """Get Object Info"""
        params = {k: v for k, v in locals().items() if k in ['bucket_name'] and v is not None}
        data = await self._request("GET", f"/objects/{object_key}", params=params)
        if data:
            return StorageObjectGet.model_validate(data)
        return data

    async def delete_storage_object_by_object_key(self, object_key: str, bucket_name: Optional[str] = None) -> Dict[str, Any]:
        """Delete Object"""
        data = await self._request("DELETE", f"/objects/{object_key}")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def post_storage_copy(self, ) -> Dict[str, Any]:
        """Copy Object"""
        data = await self._request("POST", "/copy")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def post_storage_presigned_url(self, payload: PresignedUrlRequest) -> PresignedUrlResponse:
        """Generate Presigned Url"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/presigned-url", json=json_data)
        if data:
            return PresignedUrlResponse.model_validate(data)
        return data

    async def get_storage_buckets(self, ) -> List[BucketInfo]:
        """List Buckets"""
        data = await self._request("GET", "/buckets")
        if isinstance(data, list):
            return [BucketInfo.model_validate(item) for item in data]
        return data

    async def post_storage_buckets(self, payload: BucketCreate) -> BucketInfo:
        """Create Bucket"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/buckets", json=json_data)
        if data:
            return BucketInfo.model_validate(data)
        return data

    async def delete_storage_bucket_by_bucket_name(self, bucket_name: str, force: Optional[str] = None) -> Dict[str, Any]:
        """Delete Bucket"""
        data = await self._request("DELETE", f"/buckets/{bucket_name}")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def get_storage_bucket_stat(self, bucket_name: str) -> StorageUsageStats:
        """Get Bucket Stats"""
        data = await self._request("GET", f"/buckets/{bucket_name}/stats")
        if data:
            return StorageUsageStats.model_validate(data)
        return data
