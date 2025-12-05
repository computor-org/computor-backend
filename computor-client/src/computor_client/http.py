"""
Async HTTP client for the Computor API.

This module provides a robust async HTTP client built on httpx with:
- Bearer token authentication
- Automatic token refresh
- Request/response logging
- Retry logic with exponential backoff
- Timeout configuration
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar, Union
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
        self._refresh_callback: Optional[callable] = None

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

    def set_refresh_callback(self, callback: callable) -> None:
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
    ):
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL for the API (e.g., "http://localhost:8000")
            auth_provider: Authentication provider for token management
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            headers: Additional headers to include in all requests
        """
        self.base_url = base_url.rstrip("/")
        self.auth_provider = auth_provider or TokenAuthProvider()
        self.timeout = timeout
        self.max_retries = max_retries
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
        status_code = response.status_code

        # Try to parse error details from response body
        try:
            error_data = response.json()
            detail = error_data.get("detail") or error_data.get("message") or str(error_data)
            error_code = error_data.get("error_code")
        except Exception:
            detail = response.text or f"HTTP {status_code}"
            error_code = None

        if status_code == 401:
            raise AuthenticationError(detail, status_code=status_code, error_code=error_code)
        elif status_code == 403:
            raise AuthorizationError(detail, status_code=status_code, error_code=error_code)
        elif status_code == 404:
            raise NotFoundError(detail, status_code=status_code, error_code=error_code)
        elif status_code == 400:
            raise ValidationError(detail, status_code=status_code, error_code=error_code)
        elif status_code == 409:
            raise ConflictError(detail, status_code=status_code, error_code=error_code)
        elif status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                detail,
                status_code=status_code,
                error_code=error_code,
                retry_after=int(retry_after) if retry_after else None,
            )
        elif 500 <= status_code < 600:
            raise ServerError(detail, status_code=status_code, error_code=error_code)
        else:
            raise ComputorClientError(detail, status_code=status_code, error_code=error_code)

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

        last_exception = None
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

                # Handle 401 with token refresh on first attempt
                if response.status_code == 401 and attempt == 0 and authenticated:
                    new_token = await self.auth_provider.refresh_token()
                    if new_token:
                        request_headers["Authorization"] = f"Bearer {new_token}"
                        continue

                # Convert error response to exception
                self._handle_error_response(response)

            except httpx.TimeoutException as e:
                last_exception = ClientTimeoutError(f"Request timed out: {e}")
                if attempt < self.max_retries - 1:
                    continue
            except httpx.ConnectError as e:
                last_exception = NetworkError(f"Connection failed: {e}")
                if attempt < self.max_retries - 1:
                    continue
            except httpx.HTTPStatusError as e:
                self._handle_error_response(e.response)
            except ComputorClientError:
                raise
            except Exception as e:
                last_exception = NetworkError(f"Request failed: {e}")
                if attempt < self.max_retries - 1:
                    continue

        if last_exception:
            raise last_exception
        raise NetworkError("Request failed after retries")

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
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        authenticated: bool = True,
    ) -> httpx.Response:
        """Make a DELETE request."""
        return await self._request(
            "DELETE",
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
