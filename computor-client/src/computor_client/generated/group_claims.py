"""Auto-generated client for GroupClaimInterface."""

from typing import Optional, List
import httpx

from computor_types.group_claims import (
    GroupClaimCreate,
    GroupClaimGet,
    GroupClaimQuery,
    GroupClaimUpdate,
)
from computor_client.base import BaseEndpointClient


class GroupClaimClient(BaseEndpointClient):
    """Client for group-claims endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/group-claims",
            response_model=GroupClaimGet,
            create_model=GroupClaimCreate,
            update_model=GroupClaimUpdate,
            query_model=GroupClaimQuery,
        )
