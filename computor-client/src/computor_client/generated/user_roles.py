"""Auto-generated client for UserRoleInterface."""

from typing import Optional, List
import httpx

from computor_types.user_roles import (
    UserRoleCreate,
    UserRoleGet,
    UserRoleQuery,
    UserRoleUpdate,
)
from computor_client.base import BaseEndpointClient


class UserRoleClient(BaseEndpointClient):
    """Client for user-roles endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/user-roles",
            response_model=UserRoleGet,
            create_model=UserRoleCreate,
            update_model=UserRoleUpdate,
            query_model=UserRoleQuery,
        )
