"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

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
from computor_client.urls import quote_path


class StorageClient:
    """
    Client for storage endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list_buckets(
        self,
        **kwargs: Any,
    ) -> List[BucketInfo]:
        """List Buckets"""
        response = await self._http.get(f"/storage/buckets", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [BucketInfo.model_validate(item) for item in data]
        return []

    async def buckets(
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
        await self._http.delete(f"/storage/buckets/{quote_path(bucket_name)}", params=kwargs)
        return

    async def get_buckets_stats(
        self,
        bucket_name: str,
        **kwargs: Any,
    ) -> StorageUsageStats:
        """Get Bucket Stats"""
        response = await self._http.get(f"/storage/buckets/{quote_path(bucket_name)}/stats", params=kwargs)
        return StorageUsageStats.model_validate(response.json())

    async def copy(
        self,
        source_object: str,
        dest_object: str,
        source_bucket: Optional[str] = None,
        dest_bucket: Optional[str] = None,
        metadata: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Copy Object"""
        form_fields = {k: v for k, v in {"source_object": source_object, "dest_object": dest_object, "source_bucket": source_bucket, "dest_bucket": dest_bucket, "metadata": metadata}.items() if v is not None}
        response = await self._http.post(f"/storage/copy", data=form_fields, params=kwargs)
        return response.json()

    async def get_download(
        self,
        object_key: str,
        **kwargs: Any,
    ) -> bytes:
        """Download File"""
        response = await self._http.get(f"/storage/download/{quote_path(object_key)}", params=kwargs)
        return response.content

    async def list_objects(
        self,
        **kwargs: Any,
    ) -> List[StorageObjectList]:
        """List Objects"""
        response = await self._http.get(f"/storage/objects", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [StorageObjectList.model_validate(item) for item in data]
        return []

    async def delete_objects(
        self,
        object_key: str,
        **kwargs: Any,
    ) -> None:
        """Delete Object"""
        await self._http.delete(f"/storage/objects/{quote_path(object_key)}", params=kwargs)
        return

    async def get_objects(
        self,
        object_key: str,
        **kwargs: Any,
    ) -> StorageObjectGet:
        """Get Object Info"""
        response = await self._http.get(f"/storage/objects/{quote_path(object_key)}", params=kwargs)
        return StorageObjectGet.model_validate(response.json())

    async def presigned_url(
        self,
        data: Union[PresignedUrlRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> PresignedUrlResponse:
        """Generate Presigned Url"""
        response = await self._http.post(f"/storage/presigned-url", json_data=data, params=kwargs)
        return PresignedUrlResponse.model_validate(response.json())

    async def upload(
        self,
        file: bytes,
        object_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        metadata: Optional[str] = None,
        **kwargs: Any,
    ) -> StorageObjectGet:
        """Upload File"""
        files = {"file": file}
        form_fields = {k: v for k, v in {"object_key": object_key, "bucket_name": bucket_name, "metadata": metadata}.items() if v is not None}
        response = await self._http.post(f"/storage/upload", files=files, data=form_fields, params=kwargs)
        return StorageObjectGet.model_validate(response.json())

