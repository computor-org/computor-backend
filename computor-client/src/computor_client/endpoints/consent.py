"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


from computor_client.http import AsyncHTTPClient


class ConsentClient:
    """
    Client for consent endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def status(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Consent Status"""
        response = await self._http.get(f"/consent/status", params=kwargs)
        return response.json()

    async def create(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Give Consent"""
        response = await self._http.post(f"/consent", params=kwargs)
        return response.json()

    async def withdraw(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Withdraw Consent"""
        response = await self._http.post(f"/consent/withdraw", params=kwargs)
        return response.json()

    async def policy(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Policy Text"""
        response = await self._http.get(f"/consent/policy", params=kwargs)
        return response.json()

    async def policy_versions(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Policy Versions"""
        response = await self._http.get(f"/consent/policy-versions", params=kwargs)
        return response.json()

    async def post_policy_versions(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Publish Policy Version"""
        response = await self._http.post(f"/consent/policy-versions", params=kwargs)
        return response.json()

