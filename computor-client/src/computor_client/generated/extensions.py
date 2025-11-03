"""Auto-generated client for ExtensionInterface."""

from typing import Optional, List
import httpx

from computor_types.extensions import (
    ExtensionMetadata,
    ExtensionPublishRequest,
    ExtensionVersionYankRequest,
)
from computor_client.base import BaseEndpointClient


class ExtensionClient(BaseEndpointClient):
    """Client for extensions endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/extensions",
            response_model=ExtensionMetadata,
            create_model=ExtensionPublishRequest,
            update_model=ExtensionVersionYankRequest,
        )
