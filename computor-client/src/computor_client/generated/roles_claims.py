"""Auto-generated client for RoleClaimInterface."""

from typing import Optional, List
import httpx

from computor_types.roles_claims import (
    RoleClaimGet,
    RoleClaimQuery,
)
from computor_client.base import TypedEndpointClient


class RoleClaimClient(TypedEndpointClient):
    """Client for role-claims endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/role-claims",
            response_model=RoleClaimGet,
            query_model=RoleClaimQuery,
        )
