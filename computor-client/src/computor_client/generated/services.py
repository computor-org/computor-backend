"""Auto-generated client for ServiceInterface."""

from typing import Optional, List
import httpx

from computor_types.services import (
    ServiceCreate,
    ServiceGet,
    ServiceQuery,
    ServiceUpdate,
)
from computor_client.base import TypedEndpointClient


class ServiceClient(TypedEndpointClient):
    """Client for service-accounts endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/service-accounts",
            response_model=ServiceGet,
            create_model=ServiceCreate,
            update_model=ServiceUpdate,
            query_model=ServiceQuery,
        )
