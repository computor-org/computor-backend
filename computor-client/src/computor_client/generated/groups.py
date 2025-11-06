"""Auto-generated client for GroupInterface."""

from typing import Optional, List
import httpx

from computor_types.groups import (
    GroupCreate,
    GroupGet,
    GroupQuery,
    GroupUpdate,
)
from computor_client.base import TypedEndpointClient


class GroupClient(TypedEndpointClient):
    """Client for groups endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/groups",
            response_model=GroupGet,
            create_model=GroupCreate,
            update_model=GroupUpdate,
            query_model=GroupQuery,
        )
