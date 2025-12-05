"""
Main Computor API client.

This module provides the ComputorClient class, the primary entry point
for interacting with the Computor API. It manages authentication,
endpoint clients, and session lifecycle.
"""

from typing import Any, Dict, Optional, Type, TypeVar
import logging

from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient, TokenAuthProvider
from computor_client.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    ComputorClientError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ComputorClient:
    """
    Main client for the Computor API.

    This class provides:
    - Authentication via username/password or tokens
    - Automatic token refresh
    - Lazy-loaded endpoint clients
    - Session lifecycle management

    Example usage:
        ```python
        async with ComputorClient(base_url="http://localhost:8000") as client:
            # Authenticate
            await client.login(username="admin", password="secret")

            # Use endpoint clients
            orgs = await client.organizations.list()
            user = await client.users.get("user-id")

            # Create resources
            course = await client.courses.create(CourseCreate(
                name="My Course",
                ...
            ))
        ```

    Or without context manager:
        ```python
        client = ComputorClient(base_url="http://localhost:8000")
        await client.login(username="admin", password="secret")
        # ... use client ...
        await client.close()
        ```
    """

    def __init__(
        self,
        base_url: str,
        *,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the Computor client.

        Args:
            base_url: Base URL for the API (e.g., "http://localhost:8000")
            access_token: Pre-existing access token (optional)
            refresh_token: Pre-existing refresh token (optional)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            headers: Additional headers to include in all requests
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._headers = headers or {}

        # Initialize auth provider
        self._auth_provider = TokenAuthProvider(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        # Initialize HTTP client
        self._http = AsyncHTTPClient(
            base_url=self._base_url,
            auth_provider=self._auth_provider,
            timeout=timeout,
            max_retries=max_retries,
            headers=headers,
        )

        # Setup token refresh callback
        self._auth_provider.set_refresh_callback(self._refresh_token)

        # Endpoint clients (lazy-loaded)
        self._endpoint_clients: Dict[str, Any] = {}

        # User info from last login
        self._user_id: Optional[str] = None

    @property
    def base_url(self) -> str:
        """Get the base URL for the API."""
        return self._base_url

    @property
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated."""
        return self._auth_provider.is_authenticated()

    @property
    def user_id(self) -> Optional[str]:
        """Get the user ID from the last login."""
        return self._user_id

    @property
    def http(self) -> AsyncHTTPClient:
        """Get the underlying HTTP client for custom requests."""
        return self._http

    # =========================================================================
    # Authentication
    # =========================================================================

    async def login(
        self,
        username: str,
        password: str,
    ) -> Dict[str, Any]:
        """
        Authenticate with username and password.

        Args:
            username: Username or email
            password: Password

        Returns:
            Login response with tokens and user info

        Raises:
            InvalidCredentialsError: If credentials are invalid
            AuthenticationError: If login fails for other reasons
        """
        try:
            response = await self._http.post(
                "/auth/login",
                json_data={
                    "username": username,
                    "password": password,
                },
                authenticated=False,
            )
            data = response.json()

            # Store tokens
            self._auth_provider.set_tokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
            )

            # Store user info
            self._user_id = data.get("user_id")

            logger.info(f"Successfully logged in as user: {self._user_id}")
            return data

        except AuthenticationError as e:
            # Re-raise as more specific error
            raise InvalidCredentialsError(
                str(e),
                error_code=e.error_code,
                details=e.details,
            )
        except Exception as e:
            raise AuthenticationError(f"Login failed: {e}")

    async def logout(self) -> Dict[str, Any]:
        """
        Logout and invalidate current tokens.

        Returns:
            Logout response

        Raises:
            ComputorClientError: If logout fails
        """
        try:
            response = await self._http.post("/auth/logout", authenticated=True)
            data = response.json()

            # Clear tokens
            self._auth_provider.clear_tokens()
            self._user_id = None

            logger.info("Successfully logged out")
            return data

        except Exception as e:
            # Clear tokens anyway
            self._auth_provider.clear_tokens()
            self._user_id = None
            raise ComputorClientError(f"Logout failed: {e}")

    async def _refresh_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Refresh the access token.

        This is called automatically when a request returns 401.

        Args:
            refresh_token: The refresh token

        Returns:
            Dict with new tokens, or None if refresh failed
        """
        try:
            response = await self._http.post(
                "/auth/refresh/local",
                json_data={"refresh_token": refresh_token},
                authenticated=False,
            )
            data = response.json()

            logger.debug("Successfully refreshed access token")
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", refresh_token),
            }

        except Exception as e:
            logger.warning(f"Token refresh failed: {e}")
            return None

    def set_token(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
    ) -> None:
        """
        Set authentication tokens directly.

        Use this when you have pre-existing tokens (e.g., from a stored session).

        Args:
            access_token: The access token
            refresh_token: The refresh token (optional)
        """
        self._auth_provider.set_tokens(access_token, refresh_token)
        logger.debug("Authentication tokens set")

    def clear_tokens(self) -> None:
        """Clear authentication tokens."""
        self._auth_provider.clear_tokens()
        self._user_id = None
        logger.debug("Authentication tokens cleared")

    # =========================================================================
    # Endpoint Clients
    # =========================================================================

    def _get_endpoint_client(self, client_class: Type[T]) -> T:
        """Get or create an endpoint client instance."""
        class_name = client_class.__name__
        if class_name not in self._endpoint_clients:
            self._endpoint_clients[class_name] = client_class(self._http)
        return self._endpoint_clients[class_name]

    # Endpoint client properties are generated dynamically
    # See __getattr__ for dynamic access

    def __getattr__(self, name: str) -> Any:
        """
        Dynamically access endpoint clients by name.

        This allows accessing clients like `client.organizations` without
        explicitly importing them. The client classes are imported lazily
        from the endpoints module.

        Args:
            name: Endpoint name (e.g., "organizations", "users", "courses", "auth")

        Returns:
            The endpoint client instance

        Raises:
            AttributeError: If no client exists for the given name
        """
        # Check if we've already cached this client
        if name in self._endpoint_clients:
            return self._endpoint_clients[name]

        # Convert name to expected client class name
        # e.g., "organizations" -> "OrganizationsClient"
        # e.g., "course_families" -> "CourseFamiliesClient"
        # e.g., "auth" -> "AuthenticationClient"
        parts = name.split("_")
        class_name = "".join(p.capitalize() for p in parts) + "Client"

        # Try to import the client class
        try:
            from computor_client import endpoints

            # First, try the exact name
            client_class = getattr(endpoints, class_name, None)

            # If not found, try some common aliases
            if client_class is None:
                aliases = {
                    "AuthClient": "AuthenticationClient",
                    "StorageClient": "StorageClient",
                    "UserClient": "UserClient",
                    "SystemClient": "SystemClient",
                }
                actual_name = aliases.get(class_name)
                if actual_name:
                    client_class = getattr(endpoints, actual_name, None)

            if client_class is None:
                raise AttributeError(
                    f"No endpoint client found for '{name}'. "
                    f"Expected class: {class_name}"
                )

            # Create and cache the client instance
            client = client_class(self._http)
            self._endpoint_clients[name] = client
            return client

        except ImportError as e:
            raise AttributeError(
                f"Failed to import endpoint clients. "
                f"Run 'bash generate.sh python-client' to generate them. "
                f"Error: {e}"
            )

    # =========================================================================
    # Lifecycle Management
    # =========================================================================

    async def close(self) -> None:
        """Close the client and release resources."""
        await self._http.close()
        self._endpoint_clients.clear()
        logger.debug("Client closed")

    async def __aenter__(self) -> "ComputorClient":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        await self.close()

    # =========================================================================
    # Custom Requests
    # =========================================================================

    async def get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Any:
        """
        Make a custom GET request.

        Args:
            path: Request path
            params: Query parameters
            response_model: Pydantic model for response parsing

        Returns:
            Parsed response (model instance or dict)
        """
        response = await self._http.get(path, params=params)
        data = response.json()

        if response_model:
            return response_model.model_validate(data)
        return data

    async def post(
        self,
        path: str,
        *,
        json_data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Any:
        """
        Make a custom POST request.

        Args:
            path: Request path
            json_data: JSON body data
            params: Query parameters
            response_model: Pydantic model for response parsing

        Returns:
            Parsed response (model instance or dict)
        """
        response = await self._http.post(path, json_data=json_data, params=params)
        data = response.json()

        if response_model:
            return response_model.model_validate(data)
        return data

    async def patch(
        self,
        path: str,
        *,
        json_data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Any:
        """
        Make a custom PATCH request.

        Args:
            path: Request path
            json_data: JSON body data
            params: Query parameters
            response_model: Pydantic model for response parsing

        Returns:
            Parsed response (model instance or dict)
        """
        response = await self._http.patch(path, json_data=json_data, params=params)
        data = response.json()

        if response_model:
            return response_model.model_validate(data)
        return data

    async def delete(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Make a custom DELETE request.

        Args:
            path: Request path
            params: Query parameters
        """
        await self._http.delete(path, params=params)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def health_check(self) -> bool:
        """
        Check if the API is reachable and healthy.

        Returns:
            True if the API is healthy, False otherwise
        """
        try:
            await self._http.get("/health", authenticated=False)
            return True
        except Exception:
            return False

    async def get_current_user(self) -> Dict[str, Any]:
        """
        Get the current authenticated user's information.

        Returns:
            User information dict

        Raises:
            AuthenticationError: If not authenticated
        """
        response = await self._http.get("/user/me")
        return response.json()

    def __repr__(self) -> str:
        auth_status = "authenticated" if self.is_authenticated else "not authenticated"
        return f"ComputorClient(base_url={self._base_url!r}, {auth_status})"
