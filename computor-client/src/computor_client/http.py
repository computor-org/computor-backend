"""
Async HTTP client for the Computor API.

This module provides a robust async HTTP client built on httpx with:
- Bearer token authentication
- Automatic token refresh
- Request/response logging
- Exponential-backoff retries, for idempotent methods only
- Timeout configuration
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar, Union
from urllib.parse import urljoin
import logging

import httpx
from pydantic import BaseModel

from computor_client.exceptions import (
    ComputorClientError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    ConflictError,
    RateLimitError,
    ServerError,
    NetworkError,
    TimeoutError as ClientTimeoutError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Methods that HTTP defines as idempotent, and which are therefore safe to
# replay after a transport failure. POST and PATCH are absent deliberately: a
# request that timed out may already have been applied.
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    @abstractmethod
    async def get_access_token(self) -> Optional[str]:
        """Get the current access token."""
        ...

    @abstractmethod
    async def refresh_token(self) -> Optional[str]:
        """Refresh the access token and return the new one."""
        ...

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        ...


class TokenAuthProvider(AuthProvider):
    """Simple token-based authentication provider."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._refresh_callback: Optional[Callable[[str], Awaitable[Optional[Dict[str, str]]]]] = None

    @property
    def access_token(self) -> Optional[str]:
        """The current access token, without awaiting."""
        return self._access_token

    async def get_access_token(self) -> Optional[str]:
        return self._access_token

    async def refresh_token(self) -> Optional[str]:
        if self._refresh_callback and self._refresh_token:
            new_tokens = await self._refresh_callback(self._refresh_token)
            if new_tokens:
                self._access_token = new_tokens.get("access_token")
                if "refresh_token" in new_tokens:
                    self._refresh_token = new_tokens["refresh_token"]
                return self._access_token
        return None

    def is_authenticated(self) -> bool:
        return self._access_token is not None

    def set_tokens(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
    ) -> None:
        """Set authentication tokens."""
        self._access_token = access_token
        if refresh_token is not None:
            self._refresh_token = refresh_token

    def clear_tokens(self) -> None:
        """Clear authentication tokens."""
        self._access_token = None
        self._refresh_token = None

    def set_refresh_callback(
        self,
        callback: Callable[[str], Awaitable[Optional[Dict[str, str]]]],
    ) -> None:
        """Set the callback function for token refresh."""
        self._refresh_callback = callback


class AsyncHTTPClient:
    """
    Async HTTP client for Computor API requests.

    This client handles:
    - Base URL management
    - Authentication header injection
    - Response parsing and error handling
    - Automatic retries for transient failures
    """

    def __init__(
        self,
        base_url: str,
        auth_provider: Optional[AuthProvider] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None,
        backoff_factor: float = 0.5,
        max_backoff: float = 10.0,
    ):
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL for the API (e.g., "http://localhost:8000")
            auth_provider: Authentication provider for token management
            timeout: Request timeout in seconds
            max_retries: Total attempts for a transport failure, including the
                first. Only idempotent methods are retried; see
                ``IDEMPOTENT_METHODS``.
            headers: Additional headers to include in all requests
            backoff_factor: Base delay in seconds; attempt *n* waits
                ``backoff_factor * 2**n``.
            max_backoff: Upper bound on a single backoff delay, in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.auth_provider = auth_provider or TokenAuthProvider()
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self._default_headers = headers or {}
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the underlying httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "AsyncHTTPClient":
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def _build_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Build request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self._default_headers,
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def _add_auth_header(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Add authentication header if available."""
        if self.auth_provider and self.auth_provider.is_authenticated():
            token = await self.auth_provider.get_access_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
        return headers

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Convert HTTP error responses to appropriate exceptions."""
        from computor_client.exceptions import raise_for_response

        raise_for_response(response)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Union[Dict[str, Any], BaseModel]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None,
        authenticated: bool = True,
    ) -> httpx.Response:
        """
        Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path: Request path (will be joined with base_url)
            params: Query parameters
            json_data: JSON body data (can be dict or Pydantic model)
            data: Form data
            headers: Additional headers
            files: File uploads
            authenticated: Whether to include auth header

        Returns:
            httpx.Response object

        Raises:
            ComputorClientError: On HTTP errors
            NetworkError: On connection failures
            TimeoutError: On request timeout
        """
        client = await self._get_client()

        # Build headers
        request_headers = self._build_headers(headers)
        if authenticated:
            request_headers = await self._add_auth_header(request_headers)

        # Handle Pydantic models in json_data
        if json_data is not None and isinstance(json_data, BaseModel):
            json_data = json_data.model_dump(mode="json", exclude_none=True)

        # Clean query params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        # If files are provided, remove content-type to let httpx set it
        if files:
            request_headers.pop("Content-Type", None)

        retriable = method.upper() in IDEMPOTENT_METHODS

        last_exception: Optional[ComputorClientError] = None
        for attempt in range(self.max_retries):
            try:
                response = await client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json_data,
                    data=data,
                    headers=request_headers,
                    files=files,
                )

                # Check for successful response
                if response.is_success:
                    return response

                # A 401 means the server rejected the credential, not that the
                # request was applied — so retrying after a refresh is safe for
                # every method, unlike the transient-failure retries below.
                if response.status_code == 401 and attempt == 0 and authenticated:
                    new_token = await self.auth_provider.refresh_token()
                    if new_token:
                        request_headers["Authorization"] = f"Bearer {new_token}"
                        continue

                # Convert error response to exception
                self._handle_error_response(response)

            except ComputorClientError:
                raise
            except httpx.HTTPStatusError as e:
                self._handle_error_response(e.response)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.TransportError) as e:
                if isinstance(e, httpx.TimeoutException):
                    last_exception = ClientTimeoutError(f"Request timed out: {e}")
                else:
                    last_exception = NetworkError(f"Connection failed: {e}")

                # A timed-out POST may well have been applied server-side, so
                # replaying it would duplicate the submission/message/artifact.
                # Only methods that are idempotent by HTTP semantics are retried.
                if not retriable or attempt >= self.max_retries - 1:
                    raise last_exception
                await self._sleep_before_retry(attempt)

        raise last_exception or NetworkError("Request failed after retries")

    async def _sleep_before_retry(self, attempt: int) -> None:
        """Wait before retry ``attempt`` using capped exponential backoff."""
        delay = min(self.backoff_factor * (2 ** attempt), self.max_backoff)
        logger.debug("Retrying in %.2fs (attempt %d)", delay, attempt + 1)
        await asyncio.sleep(delay)

    async def get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        authenticated: bool = True,
    ) -> httpx.Response:
        """Make a GET request."""
        return await self._request(
            "GET",
            path,
            params=params,
            headers=headers,
            authenticated=authenticated,
        )

    async def post(
        self,
        path: str,
        *,
        json_data: Optional[Union[Dict[str, Any], BaseModel]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None,
        authenticated: bool = True,
    ) -> httpx.Response:
        """Make a POST request."""
        return await self._request(
            "POST",
            path,
            json_data=json_data,
            data=data,
            params=params,
            headers=headers,
            files=files,
            authenticated=authenticated,
        )

    async def put(
        self,
        path: str,
        *,
        json_data: Optional[Union[Dict[str, Any], BaseModel]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        authenticated: bool = True,
    ) -> httpx.Response:
        """Make a PUT request."""
        return await self._request(
            "PUT",
            path,
            json_data=json_data,
            params=params,
            headers=headers,
            authenticated=authenticated,
        )

    async def patch(
        self,
        path: str,
        *,
        json_data: Optional[Union[Dict[str, Any], BaseModel]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        authenticated: bool = True,
    ) -> httpx.Response:
        """Make a PATCH request."""
        return await self._request(
            "PATCH",
            path,
            json_data=json_data,
            params=params,
            headers=headers,
            authenticated=authenticated,
        )

    async def delete(
        self,
        path: str,
        *,
        json_data: Optional[Union[Dict[str, Any], BaseModel]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        authenticated: bool = True,
    ) -> httpx.Response:
        """Make a DELETE request.

        Accepts a body: ``DELETE /documents/files`` and
        ``DELETE /documents/directories`` both require one.
        """
        return await self._request(
            "DELETE",
            path,
            json_data=json_data,
            params=params,
            headers=headers,
            authenticated=authenticated,
        )

    async def head(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        authenticated: bool = True,
    ) -> httpx.Response:
        """Make a HEAD request."""
        return await self._request(
            "HEAD",
            path,
            params=params,
            headers=headers,
            authenticated=authenticated,
        )

    # Convenience methods for typed responses

    async def get_json(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        authenticated: bool = True,
    ) -> Any:
        """Make a GET request and return JSON response."""
        response = await self.get(path, params=params, headers=headers, authenticated=authenticated)
        return response.json()

    async def post_json(
        self,
        path: str,
        *,
        json_data: Optional[Union[Dict[str, Any], BaseModel]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        authenticated: bool = True,
    ) -> Any:
        """Make a POST request and return JSON response."""
        response = await self.post(
            path,
            json_data=json_data,
            params=params,
            headers=headers,
            authenticated=authenticated,
        )
        return response.json()
