"""Auto-generated client for /role-claims endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.roles_claims import RoleClaimList

from computor_client.base import BaseEndpointClient


class RoleClaimsClient(BaseEndpointClient):
    """Client for /role-claims endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/role-claims",
        )

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_role_claims(**params)
        return await self.get_role_claims()

    async def get_role_claims(self, skip: Optional[str] = None, limit: Optional[str] = None, role_id: Optional[str] = None, claim_type: Optional[str] = None, claim_value: Optional[str] = None, user_id: Optional[str] = None) -> List[RoleClaimList]:
        """List Role Claim"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'role_id', 'claim_type', 'claim_value', 'user_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [RoleClaimList.model_validate(item) for item in data]
        return data
