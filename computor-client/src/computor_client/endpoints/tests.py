"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.results import ResultList
from computor_types.tests import TestCreate

from computor_client.http import AsyncHTTPClient


class TestsClient:
    """
    Client for tests endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        data: Union[TestCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ResultList:
        """Create Test Run"""
        response = await self._http.post(f"/tests", json_data=data, params=kwargs)
        return ResultList.model_validate(response.json())

    async def status(
        self,
        result_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Test Status"""
        response = await self._http.get(f"/tests/status/{result_id}", params=kwargs)
        return response.json()

