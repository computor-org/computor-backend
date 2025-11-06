"""Auto-generated client for ServiceTypeInterface."""

from typing import Optional, List
import httpx

from computor_types.service_type import (
    ServiceTypeCreate,
    ServiceTypeGet,
    ServiceTypeQuery,
    ServiceTypeUpdate,
)
from computor_client.base import TypedEndpointClient


class ServiceTypeClient(TypedEndpointClient):
    """Client for service-types endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/service-types",
            response_model=ServiceTypeGet,
            create_model=ServiceTypeCreate,
            update_model=ServiceTypeUpdate,
            query_model=ServiceTypeQuery,
        )
