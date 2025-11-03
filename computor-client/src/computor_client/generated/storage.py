"""Auto-generated client for StorageInterface."""

from typing import Optional, List
import httpx

from computor_types.storage import (
    StorageObjectCreate,
    StorageObjectGet,
    StorageObjectQuery,
    StorageObjectUpdate,
)
from computor_client.base import BaseEndpointClient


class StorageClient(BaseEndpointClient):
    """Client for storage endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/storage",
            response_model=StorageObjectGet,
            create_model=StorageObjectCreate,
            update_model=StorageObjectUpdate,
            query_model=StorageObjectQuery,
        )
