"""Auto-generated client for AccountInterface."""

from typing import Optional, List
import httpx

from computor_types.accounts import (
    AccountCreate,
    AccountGet,
    AccountQuery,
    AccountUpdate,
)
from computor_client.base import BaseEndpointClient


class AccountClient(BaseEndpointClient):
    """Client for accounts endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/accounts",
            response_model=AccountGet,
            create_model=AccountCreate,
            update_model=AccountUpdate,
            query_model=AccountQuery,
        )
