"""Auto-generated client for ApiTokenInterface."""

from typing import Optional, List
import httpx

from computor_types.api_tokens import (
    ApiTokenCreate,
    ApiTokenGet,
    ApiTokenQuery,
    ApiTokenUpdate,
)
from computor_client.base import TypedEndpointClient


class ApiTokenClient(TypedEndpointClient):
    """Client for api-tokens endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/api-tokens",
            response_model=ApiTokenGet,
            create_model=ApiTokenCreate,
            update_model=ApiTokenUpdate,
            query_model=ApiTokenQuery,
        )
