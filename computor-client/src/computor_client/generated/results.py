"""Auto-generated client for ResultInterface."""

from typing import Optional, List
import httpx

from computor_types.results import (
    ResultCreate,
    ResultGet,
    ResultQuery,
    ResultUpdate,
)
from computor_client.base import TypedEndpointClient


class ResultClient(TypedEndpointClient):
    """Client for results endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/results",
            response_model=ResultGet,
            create_model=ResultCreate,
            update_model=ResultUpdate,
            query_model=ResultQuery,
        )
