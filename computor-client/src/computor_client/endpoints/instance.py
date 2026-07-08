"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


from computor_client.http import AsyncHTTPClient


class InstanceClient:
    """
    Client for instance endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def instance_info(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Instance Info"""
        response = await self._http.get(f"/instance-info", params=kwargs)
        return response.json()

