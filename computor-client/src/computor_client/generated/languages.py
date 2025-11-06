"""Auto-generated client for LanguageInterface."""

from typing import Optional, List
import httpx

from computor_types.languages import (
    LanguageCreate,
    LanguageGet,
    LanguageQuery,
    LanguageUpdate,
)
from computor_client.base import TypedEndpointClient


class LanguageClient(TypedEndpointClient):
    """Client for languages endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/languages",
            response_model=LanguageGet,
            create_model=LanguageCreate,
            update_model=LanguageUpdate,
            query_model=LanguageQuery,
        )
