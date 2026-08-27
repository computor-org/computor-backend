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
from computor_client.exceptions import ComputorClientError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Attribute names whose PascalCase form does not match the generated class name,
# because the OpenAPI tag differs from how callers refer to the endpoint.
ENDPOINT_ALIASES = {
    "AuthClient": "AuthenticationClient",
    "ApiTokensClient": "TokensClient",
}


class ComputorClient:
    """
    Main client for the Computor API.

    This class provides:
    - API-token and SSO-bearer authentication
    - Automatic bearer-token refresh on 401
    - Lazy-loaded endpoint clients
    - Session lifecycle management

    Example usage:
        ```python
        async with ComputorClient(
            base_url="http://localhost:8000",
            api_token="ct_...",
        ) as client:
            # Use endpoint clients
            orgs = await client.organizations.list()
            user = await client.users.get("user-id")

            # Paginate correctly — list() gives rows, list_page() adds the total
            page = await client.organizations.list_page(skip=0, limit=50)
            print(page.total, page.has_more)

            # Create resources
            course = await client.courses.create(CourseCreate(
                title="My Course",
                ...
            ))
        ```

    Or without context manager:
        ```python
        client = ComputorClient(base_url="http://localhost:8000", api_token="ct_...")
        # ... use client ...
        await client.close()
        ```
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_token: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the Computor client.

        The API supports exactly two authentication schemes, and this client
        covers both:

        * ``api_token`` — sent as ``X-API-Token``. This is what services,
          automation and the tutor agent use.
        * ``access_token`` — an SSO bearer token obtained from the Keycloak
          browser flow, sent as ``Authorization: Bearer``. Pair it with
          ``refresh_token`` to get automatic renewal on 401.

        There is deliberately no username/password option: the API exposes no
        local credential-exchange endpoint.

        Args:
            base_url: Base URL for the API (e.g., "http://localhost:8000")
            api_token: API token for the ``X-API-Token`` header
            access_token: Pre-existing SSO bearer token (optional)
            refresh_token: Refresh token paired with ``access_token`` (optional)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            headers: Additional headers to include in all requests
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._headers = dict(headers or {})
        if api_token:
            self._headers.setdefault("X-API-Token", api_token)

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
            # self._headers, not the raw argument: it carries the
            # X-API-Token built above, without which every request is
            # anonymous and the API answers 401.
            headers=self._headers,
        )

        # Setup token refresh callback
        self._auth_provider.set_refresh_callback(self._refresh_token)

        # Endpoint clients (lazy-loaded)
        self._endpoint_clients: Dict[str, Any] = {}

    @property
    def base_url(self) -> str:
        """Get the base URL for the API."""
        return self._base_url

    @property
    def timeout(self) -> float:
        """Request timeout in seconds."""
        return self._timeout

    @property
    def auth_headers(self) -> Dict[str, str]:
        """Headers to authenticate a request made outside the async client.

        Returns the configured headers (e.g. ``X-API-Token`` for CLI token
        auth) plus a ``Bearer`` header when a session access token is present.
        Lets the sync facade authenticate without reaching into private attrs.
        """
        headers = dict(self._headers)
        token = self._auth_provider.access_token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @property
    def is_authenticated(self) -> bool:
        """True when a bearer token is set.

        Note this is only about the SSO bearer flow. With ``api_token`` auth the
        credential travels as a header on every request and there is no session
        to be in, so this stays False while requests still authenticate fine.
        """
        return self._auth_provider.is_authenticated()

    @property
    def access_token(self) -> Optional[str]:
        """The current SSO bearer token, if any.

        Public because callers legitimately need it to authenticate side
        channels the HTTP client does not cover — the agent's WebSocket
        handshake, for one, which previously reached into
        ``client._auth_provider`` to get at it.
        """
        return self._auth_provider.access_token

    async def refresh_access_token(self) -> Optional[str]:
        """Refresh the SSO bearer token, returning the new one or None."""
        return await self._auth_provider.refresh_token()

    @property
    def http(self) -> AsyncHTTPClient:
        """Get the underlying HTTP client for custom requests."""
        return self._http

    # =========================================================================
    # Authentication
    # =========================================================================

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

            self._auth_provider.clear_tokens()

            logger.info("Successfully logged out")
            return data

        except Exception as e:
            # Clear tokens anyway
            self._auth_provider.clear_tokens()
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
        logger.debug("Authentication tokens cleared")

    # =========================================================================
    # Endpoint Clients
    # =========================================================================

    # Endpoint clients are resolved dynamically; see __getattr__.

    def __getattr__(self, name: str) -> Any:
        """
        Dynamically access endpoint clients by name.

        This allows accessing clients like `client.organizations` without
        explicitly importing them. The client classes are imported lazily
        from the endpoints module and cached per attribute name.

        Args:
            name: Endpoint name (e.g., "organizations", "users", "courses")

        Returns:
            The endpoint client instance

        Raises:
            AttributeError: If no client exists for the given name
        """
        # __getattr__ runs for *any* missing attribute, including dunders probed
        # by copy/pickle and anything touched before __init__ has finished. Both
        # would recurse forever on the self._endpoint_clients lookup below.
        if name.startswith("__") or "_endpoint_clients" not in self.__dict__:
            raise AttributeError(
                f"{type(self).__name__!r} object has no attribute {name!r}"
            )

        cached = self._endpoint_clients.get(name)
        if cached is not None:
            return cached

        try:
            from computor_client import endpoints
        except ImportError as e:
            raise AttributeError(
                f"Failed to import endpoint clients. "
                f"Run 'bash generate.sh python-client' to generate them. "
                f"Error: {e}"
            ) from e

        # "course_families" -> "CourseFamiliesClient"
        class_name = "".join(part.capitalize() for part in name.split("_")) + "Client"
        client_class = getattr(endpoints, class_name, None)

        if client_class is None:
            alias = ENDPOINT_ALIASES.get(class_name)
            if alias:
                client_class = getattr(endpoints, alias, None)

        if client_class is None:
            raise AttributeError(
                f"No endpoint client found for {name!r} (looked for "
                f"{class_name}). Available: "
                f"{', '.join(sorted(getattr(endpoints, '__all__', [])))}"
            )

        client = client_class(self._http)
        self._endpoint_clients[name] = client
        return client

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
            await self._http.head("/", authenticated=False)
            return True
        except ComputorClientError:
            return False

    async def get_current_user(self) -> Dict[str, Any]:
        """
        Get the current authenticated user's information.

        Returns:
            User information dict

        Raises:
            AuthenticationError: If not authenticated
        """
        response = await self._http.get("/user")
        return response.json()

    def __repr__(self) -> str:
        auth_status = "authenticated" if self.is_authenticated else "not authenticated"
        return f"ComputorClient(base_url={self._base_url!r}, {auth_status})"
