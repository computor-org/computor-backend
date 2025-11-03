"""Auto-generated client for ExampleInterface."""

from typing import Optional, List
import httpx

from computor_types.example import (
    ExampleCreate,
    ExampleGet,
    ExampleQuery,
    ExampleUpdate,
)
from computor_client.base import BaseEndpointClient


class ExampleClient(BaseEndpointClient):
    """Client for examples endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/examples",
            response_model=ExampleGet,
            create_model=ExampleCreate,
            update_model=ExampleUpdate,
            query_model=ExampleQuery,
        )

"""Auto-generated client for ExampleRepositoryInterface."""

from typing import Optional, List
import httpx

from computor_types.example import (
    ExampleRepositoryCreate,
    ExampleRepositoryGet,
    ExampleRepositoryQuery,
    ExampleRepositoryUpdate,
)
from computor_client.base import BaseEndpointClient


class ExampleRepositoryClient(BaseEndpointClient):
    """Client for example-repositories endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/example-repositories",
            response_model=ExampleRepositoryGet,
            create_model=ExampleRepositoryCreate,
            update_model=ExampleRepositoryUpdate,
            query_model=ExampleRepositoryQuery,
        )
