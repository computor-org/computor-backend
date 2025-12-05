"""
Base classes for typed endpoint clients.

This module provides abstract base classes and mixins for building
type-safe endpoint clients with standardized CRUD operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient

# Type variables for generic typing
TCreate = TypeVar("TCreate", bound=BaseModel)
TGet = TypeVar("TGet", bound=BaseModel)
TList = TypeVar("TList", bound=BaseModel)
TUpdate = TypeVar("TUpdate", bound=BaseModel)
TQuery = TypeVar("TQuery", bound=BaseModel)


class BaseEndpointClient(ABC):
    """
    Abstract base class for all endpoint clients.

    Provides common functionality for HTTP operations and response parsing.
    """

    def __init__(
        self,
        http_client: AsyncHTTPClient,
        base_path: str,
    ):
        """
        Initialize the endpoint client.

        Args:
            http_client: The underlying HTTP client
            base_path: Base path for this endpoint (e.g., "/organizations")
        """
        self._http = http_client
        self._base_path = base_path.rstrip("/")

    @property
    def base_path(self) -> str:
        """Get the base path for this endpoint."""
        return self._base_path

    def _build_path(self, *parts: str) -> str:
        """Build a path from the base path and additional parts."""
        clean_parts = [p.strip("/") for p in parts if p]
        if clean_parts:
            return f"{self._base_path}/{'/'.join(clean_parts)}"
        return self._base_path

    def _query_to_params(self, query: Optional[BaseModel]) -> Optional[Dict[str, Any]]:
        """Convert a query model to request parameters."""
        if query is None:
            return None
        return query.model_dump(mode="json", exclude_none=True)


class ReadOnlyEndpointClient(BaseEndpointClient, Generic[TGet, TList, TQuery]):
    """
    Base class for read-only endpoint clients.

    Provides get, list, and query operations without create/update/delete.
    """

    def __init__(
        self,
        http_client: AsyncHTTPClient,
        base_path: str,
        response_model: Type[TGet],
        list_model: Optional[Type[TList]] = None,
        query_model: Optional[Type[TQuery]] = None,
    ):
        super().__init__(http_client, base_path)
        self._response_model = response_model
        self._list_model = list_model or response_model
        self._query_model = query_model

    async def get(self, id: str) -> TGet:
        """
        Get a single resource by ID.

        Args:
            id: Resource identifier

        Returns:
            The resource instance

        Raises:
            NotFoundError: If the resource doesn't exist
        """
        response = await self._http.get(self._build_path(id))
        return self._response_model.model_validate(response.json())

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        query: Optional[TQuery] = None,
        **kwargs: Any,
    ) -> List[TList]:
        """
        List resources with optional filtering.

        Args:
            skip: Number of items to skip (pagination)
            limit: Maximum number of items to return
            query: Query parameters for filtering
            **kwargs: Additional query parameters

        Returns:
            List of resources
        """
        params = {"skip": skip, "limit": limit}

        if query:
            params.update(self._query_to_params(query))
        if kwargs:
            params.update({k: v for k, v in kwargs.items() if v is not None})

        response = await self._http.get(self._base_path, params=params)
        data = response.json()

        # Handle both list and paginated responses
        if isinstance(data, list):
            return [self._list_model.model_validate(item) for item in data]
        elif isinstance(data, dict) and "items" in data:
            return [self._list_model.model_validate(item) for item in data["items"]]
        else:
            return [self._list_model.model_validate(data)]

    async def exists(self, id: str) -> bool:
        """
        Check if a resource exists.

        Args:
            id: Resource identifier

        Returns:
            True if the resource exists, False otherwise
        """
        from computor_client.exceptions import NotFoundError

        try:
            await self.get(id)
            return True
        except NotFoundError:
            return False


class CRUDEndpointClient(
    ReadOnlyEndpointClient[TGet, TList, TQuery],
    Generic[TCreate, TGet, TList, TUpdate, TQuery],
):
    """
    Base class for full CRUD endpoint clients.

    Provides create, read, update, and delete operations.
    """

    def __init__(
        self,
        http_client: AsyncHTTPClient,
        base_path: str,
        response_model: Type[TGet],
        create_model: Optional[Type[TCreate]] = None,
        update_model: Optional[Type[TUpdate]] = None,
        list_model: Optional[Type[TList]] = None,
        query_model: Optional[Type[TQuery]] = None,
    ):
        super().__init__(
            http_client,
            base_path,
            response_model=response_model,
            list_model=list_model,
            query_model=query_model,
        )
        self._create_model = create_model
        self._update_model = update_model

    async def create(self, data: Union[TCreate, Dict[str, Any]]) -> TGet:
        """
        Create a new resource.

        Args:
            data: Resource data (can be a Pydantic model or dict)

        Returns:
            The created resource

        Raises:
            ValidationError: If the data is invalid
            ConflictError: If a resource with the same identifier exists
        """
        response = await self._http.post(self._base_path, json_data=data)
        return self._response_model.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[TUpdate, Dict[str, Any]],
    ) -> TGet:
        """
        Update an existing resource.

        Args:
            id: Resource identifier
            data: Updated resource data

        Returns:
            The updated resource

        Raises:
            NotFoundError: If the resource doesn't exist
            ValidationError: If the data is invalid
        """
        response = await self._http.patch(self._build_path(id), json_data=data)
        return self._response_model.model_validate(response.json())

    async def delete(self, id: str) -> None:
        """
        Delete a resource.

        Args:
            id: Resource identifier

        Raises:
            NotFoundError: If the resource doesn't exist
        """
        await self._http.delete(self._build_path(id))

    async def create_or_update(
        self,
        id: str,
        data: Union[TCreate, TUpdate, Dict[str, Any]],
    ) -> TGet:
        """
        Create or update a resource (upsert).

        If the resource exists, it will be updated. Otherwise, a new
        resource will be created.

        Args:
            id: Resource identifier
            data: Resource data

        Returns:
            The created or updated resource
        """
        if await self.exists(id):
            return await self.update(id, data)
        else:
            # For create, we might need to add the ID to the data
            if isinstance(data, dict):
                data["id"] = id
            return await self.create(data)


class TypedEndpointClient(BaseEndpointClient):
    """
    Flexible typed endpoint client that auto-configures based on available models.

    This is the primary base class used by generated clients. It provides
    type-safe operations based on which models are configured.
    """

    def __init__(
        self,
        http_client: AsyncHTTPClient,
        base_path: str,
        response_model: Optional[Type[BaseModel]] = None,
        create_model: Optional[Type[BaseModel]] = None,
        update_model: Optional[Type[BaseModel]] = None,
        list_model: Optional[Type[BaseModel]] = None,
        query_model: Optional[Type[BaseModel]] = None,
    ):
        super().__init__(http_client, base_path)
        self._response_model = response_model
        self._create_model = create_model
        self._update_model = update_model
        self._list_model = list_model or response_model
        self._query_model = query_model

    # =========================================================================
    # Read Operations
    # =========================================================================

    async def get(self, id: str) -> BaseModel:
        """
        Get a single resource by ID.

        Args:
            id: Resource identifier

        Returns:
            The resource instance

        Raises:
            NotFoundError: If the resource doesn't exist
            RuntimeError: If no response model is configured
        """
        if not self._response_model:
            raise RuntimeError(f"No response model configured for {self._base_path}")

        response = await self._http.get(self._build_path(id))
        return self._response_model.model_validate(response.json())

    async def get_raw(self, id: str) -> Dict[str, Any]:
        """Get a resource as a raw dictionary."""
        response = await self._http.get(self._build_path(id))
        return response.json()

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[BaseModel]:
        """
        List resources with optional filtering.

        Args:
            skip: Number of items to skip (pagination)
            limit: Maximum number of items to return
            query: Query parameters for filtering
            **kwargs: Additional query parameters

        Returns:
            List of resources
        """
        if not self._list_model:
            raise RuntimeError(f"No list model configured for {self._base_path}")

        params = {"skip": skip, "limit": limit}

        if query:
            params.update(self._query_to_params(query))
        if kwargs:
            params.update({k: v for k, v in kwargs.items() if v is not None})

        response = await self._http.get(self._base_path, params=params)
        data = response.json()

        if isinstance(data, list):
            return [self._list_model.model_validate(item) for item in data]
        elif isinstance(data, dict) and "items" in data:
            return [self._list_model.model_validate(item) for item in data["items"]]
        else:
            return [self._list_model.model_validate(data)]

    async def list_raw(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """List resources as raw dictionaries."""
        params = {"skip": skip, "limit": limit, **kwargs}
        params = {k: v for k, v in params.items() if v is not None}

        response = await self._http.get(self._base_path, params=params)
        data = response.json()

        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "items" in data:
            return data["items"]
        else:
            return [data]

    async def exists(self, id: str) -> bool:
        """Check if a resource exists."""
        from computor_client.exceptions import NotFoundError

        try:
            await self.get_raw(id)
            return True
        except NotFoundError:
            return False

    # =========================================================================
    # Write Operations
    # =========================================================================

    async def create(self, data: Union[BaseModel, Dict[str, Any]]) -> BaseModel:
        """
        Create a new resource.

        Args:
            data: Resource data (can be a Pydantic model or dict)

        Returns:
            The created resource

        Raises:
            RuntimeError: If no create or response model is configured
        """
        if not self._response_model:
            raise RuntimeError(f"No response model configured for {self._base_path}")

        response = await self._http.post(self._base_path, json_data=data)
        return self._response_model.model_validate(response.json())

    async def create_raw(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a resource and return raw dictionary."""
        response = await self._http.post(self._base_path, json_data=data)
        return response.json()

    async def update(
        self,
        id: str,
        data: Union[BaseModel, Dict[str, Any]],
    ) -> BaseModel:
        """
        Update an existing resource.

        Args:
            id: Resource identifier
            data: Updated resource data

        Returns:
            The updated resource
        """
        if not self._response_model:
            raise RuntimeError(f"No response model configured for {self._base_path}")

        response = await self._http.patch(self._build_path(id), json_data=data)
        return self._response_model.model_validate(response.json())

    async def update_raw(
        self,
        id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a resource and return raw dictionary."""
        response = await self._http.patch(self._build_path(id), json_data=data)
        return response.json()

    async def delete(self, id: str) -> None:
        """
        Delete a resource.

        Args:
            id: Resource identifier
        """
        await self._http.delete(self._build_path(id))

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def count(self, query: Optional[BaseModel] = None, **kwargs: Any) -> int:
        """
        Get the count of resources matching the query.

        Note: This makes a list request with limit=0 to get the count.
        The actual implementation depends on the API returning a total count.
        """
        params = {"skip": 0, "limit": 0}
        if query:
            params.update(self._query_to_params(query))
        if kwargs:
            params.update({k: v for k, v in kwargs.items() if v is not None})

        response = await self._http.get(self._base_path, params=params)
        data = response.json()

        if isinstance(data, dict) and "total" in data:
            return data["total"]
        elif isinstance(data, list):
            return len(data)
        return 0

    async def get_all(
        self,
        *,
        query: Optional[BaseModel] = None,
        batch_size: int = 100,
        **kwargs: Any,
    ) -> List[BaseModel]:
        """
        Get all resources matching the query (with pagination).

        This method automatically handles pagination to retrieve all
        matching resources.

        Args:
            query: Query parameters for filtering
            batch_size: Number of items to fetch per request
            **kwargs: Additional query parameters

        Returns:
            List of all matching resources
        """
        all_items = []
        skip = 0

        while True:
            items = await self.list(
                skip=skip,
                limit=batch_size,
                query=query,
                **kwargs,
            )
            if not items:
                break
            all_items.extend(items)
            if len(items) < batch_size:
                break
            skip += batch_size

        return all_items
