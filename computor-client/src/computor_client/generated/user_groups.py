"""Auto-generated client for UserGroupInterface."""

from typing import Optional, List
import httpx

from computor_types.user_groups import (
    UserGroupCreate,
    UserGroupGet,
    UserGroupQuery,
    UserGroupUpdate,
)
from computor_client.base import BaseEndpointClient


class UserGroupClient(BaseEndpointClient):
    """Client for user-groups endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/user-groups",
            response_model=UserGroupGet,
            create_model=UserGroupCreate,
            update_model=UserGroupUpdate,
            query_model=UserGroupQuery,
        )
