"""Auto-generated client for SessionInterface."""

from typing import Optional, List
import httpx

from computor_types.sessions import (
    SessionCreate,
    SessionGet,
    SessionQuery,
    SessionUpdate,
)
from computor_client.base import TypedEndpointClient


class SessionClient(TypedEndpointClient):
    """Client for sessions endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/sessions",
            response_model=SessionGet,
            create_model=SessionCreate,
            update_model=SessionUpdate,
            query_model=SessionQuery,
        )
