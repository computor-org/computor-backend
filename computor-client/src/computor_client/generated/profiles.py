"""Auto-generated client for ProfileInterface."""

from typing import Optional, List
import httpx

from computor_types.profiles import (
    ProfileCreate,
    ProfileGet,
    ProfileQuery,
    ProfileUpdate,
)
from computor_client.base import BaseEndpointClient


class ProfileClient(BaseEndpointClient):
    """Client for profiles endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/profiles",
            response_model=ProfileGet,
            create_model=ProfileCreate,
            update_model=ProfileUpdate,
            query_model=ProfileQuery,
        )
