"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any

from computor_types.instance import InstanceStatusGet

from computor_client.http import AsyncHTTPClient


class InstanceStatusClient:
    """
    Client for instance status endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def get(
        self,
        **kwargs: Any,
    ) -> InstanceStatusGet:
        """Get Instance Status"""
        response = await self._http.get("/instance-status", params=kwargs)
        return InstanceStatusGet.model_validate(response.json())

