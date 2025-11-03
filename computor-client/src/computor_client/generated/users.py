"""Auto-generated client for UserInterface."""

from typing import Optional, List
import httpx

from computor_types.users import (
    UserCreate,
    UserGet,
    UserQuery,
    UserUpdate,
)
from computor_client.base import BaseEndpointClient


class UserClient(BaseEndpointClient):
    """Client for users endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/users",
            response_model=UserGet,
            create_model=UserCreate,
            update_model=UserUpdate,
            query_model=UserQuery,
        )
