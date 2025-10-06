"""Base client classes for Computor API."""

from typing import TypeVar, Generic, Optional, Type, Dict, Any, List
import httpx
from pydantic import BaseModel

from .exceptions import raise_for_status


T = TypeVar('T', bound=BaseModel)
CreateT = TypeVar('CreateT', bound=BaseModel)
UpdateT = TypeVar('UpdateT', bound=BaseModel)
QueryT = TypeVar('QueryT', bound=BaseModel)


class BaseEndpointClient(Generic[T, CreateT, UpdateT, QueryT]):
    """Base class for CRUD endpoint clients."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_path: str,
        response_model: Type[T],
        create_model: Optional[Type[CreateT]] = None,
        update_model: Optional[Type[UpdateT]] = None,
        query_model: Optional[Type[QueryT]] = None,
    ):
        self.client = client
        self.base_path = base_path.rstrip('/')
        self.response_model = response_model
        self.create_model = create_model
        self.update_model = update_model
        self.query_model = query_model

    def _build_path(self, *segments: Any) -> str:
        """Build URL path from base path and segments."""
        if not segments:
            return self.base_path

        encoded_segments = [str(seg) for seg in segments]
        joined = '/'.join(encoded_segments)

        if self.base_path == '/':
            return f"/{joined}"

        return f"{self.base_path}/{joined}"

    async def create(self, payload: CreateT) -> T:
        """Create a new entity."""
        if not self.create_model:
            raise NotImplementedError("Create operation not supported")

        response = await self.client.post(
            self.base_path,
            json=payload.model_dump(mode='json', exclude_unset=True)
        )

        # Handle errors
        if response.status_code >= 400:
            raise_for_status(response.status_code, response.json())

        response.raise_for_status()
        return self.response_model.model_validate(response.json())

    async def get(self, id: str) -> T:
        """Get entity by ID."""
        response = await self.client.get(self._build_path(id))

        # Handle errors
        if response.status_code >= 400:
            raise_for_status(response.status_code, response.json())

        response.raise_for_status()
        return self.response_model.model_validate(response.json())

    async def list(self, params: Optional[QueryT] = None) -> List[T]:
        """List entities with optional query parameters."""
        query_params = {}
        if params:
            query_params = params.model_dump(mode='json', exclude_unset=True)

        response = await self.client.get(self.base_path, params=query_params)

        # Handle errors
        if response.status_code >= 400:
            raise_for_status(response.status_code, response.json())

        response.raise_for_status()
        return [self.response_model.model_validate(item) for item in response.json()]

    async def update(self, id: str, payload: UpdateT) -> T:
        """Update an existing entity."""
        if not self.update_model:
            raise NotImplementedError("Update operation not supported")

        response = await self.client.patch(
            self._build_path(id),
            json=payload.model_dump(mode='json', exclude_unset=True)
        )

        # Handle errors
        if response.status_code >= 400:
            raise_for_status(response.status_code, response.json())

        response.raise_for_status()
        return self.response_model.model_validate(response.json())

    async def delete(self, id: str) -> None:
        """Delete an entity."""
        response = await self.client.delete(self._build_path(id))

        # Handle errors
        if response.status_code >= 400:
            raise_for_status(response.status_code, response.json())

        response.raise_for_status()

    async def archive(self, id: str) -> None:
        """Archive an entity (if supported)."""
        response = await self.client.patch(self._build_path(id, 'archive'))

        # Handle errors
        if response.status_code >= 400:
            raise_for_status(response.status_code, response.json())

        response.raise_for_status()
