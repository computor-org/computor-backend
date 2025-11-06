"""Auto-generated client for MessageInterface."""

from typing import Optional, List
import httpx

from computor_types.messages import (
    MessageCreate,
    MessageGet,
    MessageQuery,
    MessageUpdate,
)
from computor_client.base import TypedEndpointClient


class MessageClient(TypedEndpointClient):
    """Client for messages endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/messages",
            response_model=MessageGet,
            create_model=MessageCreate,
            update_model=MessageUpdate,
            query_model=MessageQuery,
        )
