"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.storage import (
    BucketCreate,
    BucketInfo,
    PresignedUrlRequest,
    PresignedUrlResponse,
    StorageObjectGet,
    StorageObjectList,
    StorageUsageStats,
)

from computor_client.http import AsyncHTTPClient


class StorageClient:
    """
    Client for storage endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def upload(
        self,
        **kwargs: Any,
    ) -> StorageObjectGet:
        """Upload File"""
        response = await self._http.post(f"/storage/upload", params=kwargs)
        return StorageObjectGet.model_validate(response.json())

    async def download(
        self,
        object_key: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Download File"""
        response = await self._http.get(f"/storage/download/{object_key}", params=kwargs)
        return response.json()

    async def objects(
        self,
        **kwargs: Any,
    ) -> List[StorageObjectList]:
        """List Objects"""
        response = await self._http.get(f"/storage/objects", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [StorageObjectList.model_validate(item) for item in data]
        return []

    async def get_objects(
        self,
        object_key: str,
        **kwargs: Any,
    ) -> StorageObjectGet:
        """Get Object Info"""
        response = await self._http.get(f"/storage/objects/{object_key}", params=kwargs)
        return StorageObjectGet.model_validate(response.json())

    async def delete_objects(
        self,
        object_key: str,
        **kwargs: Any,
    ) -> None:
        """Delete Object"""
        await self._http.delete(f"/storage/objects/{object_key}", params=kwargs)
        return

    async def copy(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Copy Object"""
        response = await self._http.post(f"/storage/copy", params=kwargs)
        return response.json()

    async def presigned_url(
        self,
        data: Union[PresignedUrlRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> PresignedUrlResponse:
        """Generate Presigned Url"""
        response = await self._http.post(f"/storage/presigned-url", json_data=data, params=kwargs)
        return PresignedUrlResponse.model_validate(response.json())

    async def buckets(
        self,
        **kwargs: Any,
    ) -> List[BucketInfo]:
        """List Buckets"""
        response = await self._http.get(f"/storage/buckets", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [BucketInfo.model_validate(item) for item in data]
        return []

    async def post_buckets(
        self,
        data: Union[BucketCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> BucketInfo:
        """Create Bucket"""
        response = await self._http.post(f"/storage/buckets", json_data=data, params=kwargs)
        return BucketInfo.model_validate(response.json())

    async def delete_buckets(
        self,
        bucket_name: str,
        **kwargs: Any,
    ) -> None:
        """Delete Bucket"""
        await self._http.delete(f"/storage/buckets/{bucket_name}", params=kwargs)
        return

    async def buckets_stats(
        self,
        bucket_name: str,
        **kwargs: Any,
    ) -> StorageUsageStats:
        """Get Bucket Stats"""
        response = await self._http.get(f"/storage/buckets/{bucket_name}/stats", params=kwargs)
        return StorageUsageStats.model_validate(response.json())

