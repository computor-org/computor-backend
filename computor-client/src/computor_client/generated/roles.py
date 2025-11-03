"""Auto-generated client for RoleInterface."""

from typing import Optional, List
import httpx

from computor_types.roles import (
    RoleGet,
    RoleQuery,
)
from computor_client.base import BaseEndpointClient


class RoleClient(BaseEndpointClient):
    """Client for roles endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/roles",
            response_model=RoleGet,
            query_model=RoleQuery,
        )
