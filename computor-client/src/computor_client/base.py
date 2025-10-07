"""Base client classes for Computor API.

This module provides a unified hierarchy of client base classes:

1. SimpleEndpointClient - Minimal untyped base for auto-generated clients
2. TypedEndpointClient - Strongly-typed generic CRUD client with Pydantic validation
3. CustomActionClient - Base for endpoints with custom actions beyond CRUD
4. Specialized clients - Role-based, file operations, tasks, authentication

The hierarchy allows flexibility (simple/untyped) while providing type safety when needed.
"""

from __future__ import annotations

from typing import TypeVar, Generic, Optional, Type, Dict, Any, List, Union
from pathlib import Path
import httpx
from pydantic import BaseModel

from .exceptions import raise_for_status


# Type variables for generic typed clients
T = TypeVar('T', bound=BaseModel)
CreateT = TypeVar('CreateT', bound=BaseModel)
UpdateT = TypeVar('UpdateT', bound=BaseModel)
QueryT = TypeVar('QueryT', bound=BaseModel)


# ============================================================================
# Base Client Classes
# ============================================================================


class SimpleEndpointClient:
    """Minimal base class for auto-generated endpoint clients (untyped).

    This class provides basic HTTP request functionality without type validation.
    It's used by auto-generated clients that need flexibility and don't require
    strict Pydantic model validation.

    For type-safe clients with automatic validation, use TypedEndpointClient instead.
    """

    def __init__(self, client: httpx.AsyncClient, base_path: str):
        self.client = client
        self.base_path = base_path.rstrip('/')

    def _build_path(self, *segments: Any) -> str:
        """Build URL path from base path and segments."""
        if not segments:
            return self.base_path

        encoded_segments = [str(seg) for seg in segments]
        joined = '/'.join(encoded_segments)

        if self.base_path == '/':
            return f"/{joined}"

        return f"{self.base_path}/{joined}"

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Make an HTTP request and return the response data."""
        # Build full URL
        url = self.base_path + (f"/{path}" if path and not path.startswith('/') else path)

        response = await self.client.request(
            method=method,
            url=url,
            json=json,
            params=params,
            files=files,
            **kwargs
        )

        # Handle errors
        if response.status_code >= 400:
            raise_for_status(response.status_code, response.json())

        response.raise_for_status()

        # Return response data
        if response.content:
            return response.json()
        return None

    # Generic CRUD method aliases for backward compatibility
    async def create(self, payload: BaseModel) -> Any:
        """Create a new entity (generic wrapper for POST)."""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        return await self._request("POST", "", json=json_data)

    async def list(self, query: Optional[BaseModel] = None) -> List[Any]:
        """List entities (generic wrapper for GET with params)."""
        params = {}
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
        return await self._request("GET", "", params=params)

    async def get(self, id: str) -> Any:
        """Get entity by ID (generic wrapper for GET /{id})."""
        return await self._request("GET", f"/{id}")

    async def update(self, id: str, payload: BaseModel) -> Any:
        """Update an entity (generic wrapper for PATCH /{id})."""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        return await self._request("PATCH", f"/{id}", json=json_data)

    async def delete(self, id: str) -> Any:
        """Delete an entity (generic wrapper for DELETE /{id})."""
        return await self._request("DELETE", f"/{id}")


class TypedEndpointClient(Generic[T, CreateT, UpdateT, QueryT]):
    """Strongly-typed base class for CRUD endpoint clients.

    This class provides type-safe CRUD operations with automatic Pydantic validation.
    All operations return properly validated Pydantic models with full type hints.

    Type Parameters:
        T: Response model type (e.g., OrganizationGet)
        CreateT: Create payload model type (e.g., OrganizationCreate)
        UpdateT: Update payload model type (e.g., OrganizationUpdate)
        QueryT: Query parameters model type (e.g., OrganizationQuery)

    Example:
        ```python
        client = TypedEndpointClient(
            client=http_client,
            base_path="/organizations",
            response_model=OrganizationGet,
            create_model=OrganizationCreate,
            update_model=OrganizationUpdate,
            query_model=OrganizationQuery,
        )

        # Returns validated OrganizationGet instance
        org = await client.get("123")
        ```
    """

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


# ============================================================================
# Specialized Client Classes
# ============================================================================


class CustomActionClient(Generic[T]):
    """Base class for clients with custom actions beyond CRUD.

    This class extends SimpleEndpointClient with support for custom action methods
    and optional Pydantic model validation. It's ideal for endpoints that don't
    follow standard CRUD patterns.

    Features:
    - Custom HTTP methods (custom_get, custom_post, custom_patch, custom_delete)
    - Optional response model validation
    - Flexible payload handling (BaseModel or Dict)

    Example:
        ```python
        class MyCustomClient(CustomActionClient):
            async def special_action(self, id: str):
                return await self.custom_post(
                    f"{id}/special",
                    {"param": "value"},
                    response_model=MyResponseModel
                )
        ```
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_path: str,
        response_model: Optional[Type[T]] = None,
    ):
        self.client = client
        self.base_path = base_path.rstrip('/')
        self.response_model = response_model

    def _build_path(self, *segments: Any) -> str:
        """Build URL path from base path and segments."""
        if not segments:
            return self.base_path

        encoded_segments = [str(seg) for seg in segments]
        joined = '/'.join(encoded_segments)

        if self.base_path == '/':
            return f"/{joined}"

        return f"{self.base_path}/{joined}"

    async def _request(
        self,
        method: str,
        path: str = "",
        response_model: Optional[Type[BaseModel]] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Generic request method with error handling."""
        url = self._build_path(path) if path else self.base_path

        response = await self.client.request(
            method=method,
            url=url,
            json=json,
            params=params,
            files=files,
            **kwargs
        )

        # Handle errors
        if response.status_code >= 400:
            raise_for_status(response.status_code, response.json())

        response.raise_for_status()

        # Parse response if model provided
        if response.content:
            data = response.json()
            model = response_model or self.response_model
            if model:
                if isinstance(data, list):
                    return [model.model_validate(item) for item in data]
                return model.model_validate(data)
            return data
        return None

    async def custom_get(
        self,
        action: str,
        response_model: Optional[Type[BaseModel]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """GET request to a custom action endpoint."""
        return await self._request("GET", action, response_model, params=params)

    async def custom_post(
        self,
        action: str,
        payload: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        response_model: Optional[Type[BaseModel]] = None,
        **kwargs
    ) -> Any:
        """POST request to a custom action endpoint."""
        json_data = None
        if payload:
            if isinstance(payload, BaseModel):
                json_data = payload.model_dump(mode='json', exclude_unset=True)
            else:
                json_data = payload

        return await self._request("POST", action, response_model, json=json_data, **kwargs)

    async def custom_patch(
        self,
        action: str,
        payload: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Any:
        """PATCH request to a custom action endpoint."""
        json_data = None
        if payload:
            if isinstance(payload, BaseModel):
                json_data = payload.model_dump(mode='json', exclude_unset=True)
            else:
                json_data = payload

        return await self._request("PATCH", action, response_model, json=json_data)

    async def custom_delete(
        self,
        action: str,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Any:
        """DELETE request to a custom action endpoint."""
        return await self._request("DELETE", action, response_model)


class RoleBasedViewClient(CustomActionClient[T]):
    """Base class for role-based view endpoints (students, tutors, lecturers).

    Provides common methods for role-specific course and course content access.
    """

    async def get_course(self, course_id: str, response_model: Optional[Type[BaseModel]] = None) -> Any:
        """Get course view for this role."""
        return await self.custom_get(f"courses/{course_id}", response_model)

    async def list_courses(
        self,
        response_model: Optional[Type[BaseModel]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """List courses for this role."""
        return await self.custom_get("courses", response_model, params=params)

    async def get_course_content(
        self,
        course_content_id: str,
        response_model: Optional[Type[BaseModel]] = None
    ) -> Any:
        """Get course content view for this role."""
        return await self.custom_get(f"course-contents/{course_content_id}", response_model)

    async def list_course_contents(
        self,
        response_model: Optional[Type[BaseModel]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """List course contents for this role."""
        return await self.custom_get("course-contents", response_model, params=params)


class FileOperationClient(CustomActionClient[T]):
    """Base class for file upload/download operations.

    Provides methods for file handling including uploads, downloads, and streaming.
    """

    async def upload_file(
        self,
        file_path: Union[str, Path],
        endpoint: str = "upload",
        additional_data: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Any:
        """Upload a file to the endpoint."""
        file_path = Path(file_path)

        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/octet-stream')}

            # Add additional form data if provided
            data = additional_data or {}

            response = await self.client.post(
                self._build_path(endpoint),
                files=files,
                data=data
            )

            if response.status_code >= 400:
                raise_for_status(response.status_code, response.json())

            response.raise_for_status()

            if response.content:
                data = response.json()
                model = response_model or self.response_model
                if model:
                    return model.model_validate(data)
                return data
            return None

    async def download_file(
        self,
        endpoint: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> bytes:
        """Download a file from the endpoint."""
        response = await self.client.get(self._build_path(endpoint))

        if response.status_code >= 400:
            raise_for_status(response.status_code, response.json())

        response.raise_for_status()

        content = response.content

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(content)

        return content

    async def stream_download(
        self,
        endpoint: str,
        output_path: Union[str, Path],
        chunk_size: int = 8192,
    ) -> None:
        """Stream download a large file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async with self.client.stream("GET", self._build_path(endpoint)) as response:
            if response.status_code >= 400:
                data = await response.aread()
                raise_for_status(response.status_code, data)

            response.raise_for_status()

            with open(output_path, 'wb') as f:
                async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                    f.write(chunk)


class TaskClient(CustomActionClient[T]):
    """Base class for task/workflow management endpoints.

    Provides methods for submitting tasks, checking status, and retrieving results.
    """

    async def submit_task(
        self,
        payload: Union[BaseModel, Dict[str, Any]],
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Any:
        """Submit a task for execution."""
        return await self.custom_post("submit", payload, response_model)

    async def get_status(
        self,
        task_id: str,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Any:
        """Get task execution status."""
        return await self.custom_get(f"{task_id}/status", response_model)

    async def get_result(
        self,
        task_id: str,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Any:
        """Get task execution result."""
        return await self.custom_get(f"{task_id}/result", response_model)

    async def cancel_task(
        self,
        task_id: str,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Any:
        """Cancel a running task."""
        return await self.custom_delete(f"{task_id}/cancel", response_model)

    async def list_tasks(
        self,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> List[Any]:
        """List tasks with optional filtering."""
        return await self.custom_get("", response_model, params=params)


class AuthenticationClient(CustomActionClient[T]):
    """Base class for authentication endpoints.

    Provides methods for login, logout, token refresh, and SSO operations.
    """

    async def login(
        self,
        username: str,
        password: str,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Any:
        """Login with username and password."""
        return await self.custom_post(
            "login",
            {"username": username, "password": password},
            response_model
        )

    async def logout(self, response_model: Optional[Type[BaseModel]] = None) -> Any:
        """Logout from current session."""
        return await self.custom_post("logout", None, response_model)

    async def refresh_token(
        self,
        refresh_token: str,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Any:
        """Refresh access token."""
        return await self.custom_post(
            "refresh",
            {"refresh_token": refresh_token},
            response_model
        )

    async def get_providers(self, response_model: Optional[Type[BaseModel]] = None) -> List[Any]:
        """Get list of authentication providers."""
        return await self.custom_get("providers", response_model)

    async def sso_login(
        self,
        provider: str,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Any:
        """Initiate SSO login with provider."""
        return await self.custom_get(f"{provider}/login", response_model)


# Backward compatibility aliases
BaseEndpointClient = SimpleEndpointClient  # For generated clients
