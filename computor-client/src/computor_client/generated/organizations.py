"""Auto-generated client for OrganizationInterface."""

from typing import Optional, List
import httpx

from computor_types.organizations import (
    OrganizationCreate,
    OrganizationGet,
    OrganizationQuery,
    OrganizationUpdate,
)
from computor_client.base import TypedEndpointClient


class OrganizationClient(TypedEndpointClient):
    """Client for organizations endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/organizations",
            response_model=OrganizationGet,
            create_model=OrganizationCreate,
            update_model=OrganizationUpdate,
            query_model=OrganizationQuery,
        )
