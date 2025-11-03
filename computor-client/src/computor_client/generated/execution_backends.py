"""Auto-generated client for ExecutionBackendInterface."""

from typing import Optional, List
import httpx

from computor_types.execution_backends import (
    ExecutionBackendCreate,
    ExecutionBackendGet,
    ExecutionBackendQuery,
    ExecutionBackendUpdate,
)
from computor_client.base import BaseEndpointClient


class ExecutionBackendClient(BaseEndpointClient):
    """Client for execution-backends endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/execution-backends",
            response_model=ExecutionBackendGet,
            create_model=ExecutionBackendCreate,
            update_model=ExecutionBackendUpdate,
            query_model=ExecutionBackendQuery,
        )
