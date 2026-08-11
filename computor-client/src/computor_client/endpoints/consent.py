"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Union

from computor_types.consent import (
    ConsentCreate,
    ConsentStatusGet,
    PolicyTextGet,
    PolicyVersionCreate,
    PolicyVersionGet,
)

from computor_client.http import AsyncHTTPClient


class ConsentClient:
    """
    Client for consent endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        data: Union[ConsentCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ConsentStatusGet:
        """Give Consent"""
        response = await self._http.post("/consent", json_data=data, params=kwargs)
        return ConsentStatusGet.model_validate(response.json())

    async def get_policy(
        self,
        **kwargs: Any,
    ) -> PolicyTextGet:
        """Get Policy Text"""
        response = await self._http.get("/consent/policy", params=kwargs)
        return PolicyTextGet.model_validate(response.json())

    async def list_policy_versions(
        self,
        **kwargs: Any,
    ) -> List[PolicyVersionGet]:
        """List Policy Versions"""
        response = await self._http.get("/consent/policy-versions", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [PolicyVersionGet.model_validate(item) for item in data]
        return []

    async def policy_versions(
        self,
        data: Union[PolicyVersionCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> PolicyVersionGet:
        """Publish Policy Version"""
        response = await self._http.post("/consent/policy-versions", json_data=data, params=kwargs)
        return PolicyVersionGet.model_validate(response.json())

    async def get_status(
        self,
        **kwargs: Any,
    ) -> ConsentStatusGet:
        """Get Consent Status"""
        response = await self._http.get("/consent/status", params=kwargs)
        return ConsentStatusGet.model_validate(response.json())

    async def withdraw(
        self,
        **kwargs: Any,
    ) -> ConsentStatusGet:
        """Withdraw Consent"""
        response = await self._http.post("/consent/withdraw", params=kwargs)
        return ConsentStatusGet.model_validate(response.json())

