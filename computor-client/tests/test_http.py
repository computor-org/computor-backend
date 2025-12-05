"""Tests for the HTTP client module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from computor_client.http import (
    AsyncHTTPClient,
    TokenAuthProvider,
    AuthProvider,
)
from computor_client.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    ServerError,
    NetworkError,
    TimeoutError as ClientTimeoutError,
)


class TestTokenAuthProvider:
    """Tests for the TokenAuthProvider class."""

    def test_initialization_without_tokens(self):
        """Test creating provider without tokens."""
        provider = TokenAuthProvider()
        assert not provider.is_authenticated()

    def test_initialization_with_tokens(self):
        """Test creating provider with tokens."""
        provider = TokenAuthProvider(
            access_token="test-access",
            refresh_token="test-refresh",
        )
        assert provider.is_authenticated()

    @pytest.mark.asyncio
    async def test_get_access_token(self):
        """Test getting access token."""
        provider = TokenAuthProvider(access_token="test-token")
        token = await provider.get_access_token()
        assert token == "test-token"

    def test_set_tokens(self):
        """Test setting tokens."""
        provider = TokenAuthProvider()
        assert not provider.is_authenticated()

        provider.set_tokens("new-access", "new-refresh")
        assert provider.is_authenticated()

    def test_clear_tokens(self):
        """Test clearing tokens."""
        provider = TokenAuthProvider(access_token="test")
        assert provider.is_authenticated()

        provider.clear_tokens()
        assert not provider.is_authenticated()

    @pytest.mark.asyncio
    async def test_refresh_token_with_callback(self):
        """Test refreshing token with callback."""
        provider = TokenAuthProvider(
            access_token="old-token",
            refresh_token="refresh-token",
        )

        async def mock_refresh(refresh_token):
            return {
                "access_token": "new-token",
                "refresh_token": "new-refresh",
            }

        provider.set_refresh_callback(mock_refresh)

        new_token = await provider.refresh_token()
        assert new_token == "new-token"
        assert await provider.get_access_token() == "new-token"

    @pytest.mark.asyncio
    async def test_refresh_token_without_callback(self):
        """Test refreshing token without callback returns None."""
        provider = TokenAuthProvider(refresh_token="refresh")
        result = await provider.refresh_token()
        assert result is None


class TestAsyncHTTPClient:
    """Tests for the AsyncHTTPClient class."""

    @pytest.fixture
    def client(self):
        """Create a client for testing."""
        return AsyncHTTPClient(base_url="http://localhost:8000")

    def test_initialization(self, client):
        """Test client initialization."""
        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 30.0
        assert client.max_retries == 3

    def test_initialization_with_trailing_slash(self):
        """Test that trailing slashes are stripped from base_url."""
        client = AsyncHTTPClient(base_url="http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"

    def test_initialization_with_custom_settings(self):
        """Test client with custom settings."""
        client = AsyncHTTPClient(
            base_url="http://api.example.com",
            timeout=60.0,
            max_retries=5,
            headers={"X-Custom": "value"},
        )
        assert client.timeout == 60.0
        assert client.max_retries == 5

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client as context manager."""
        async with AsyncHTTPClient(base_url="http://localhost:8000") as client:
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test closing the client."""
        await client._get_client()  # Initialize the client
        await client.close()
        assert client._client is None or client._client.is_closed

    def test_build_headers(self, client):
        """Test building request headers."""
        headers = client._build_headers()
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    def test_build_headers_with_extra(self, client):
        """Test building headers with extra headers."""
        headers = client._build_headers({"X-Custom": "value"})
        assert headers["X-Custom"] == "value"

    @pytest.mark.asyncio
    async def test_add_auth_header(self, client):
        """Test adding authentication header."""
        client.auth_provider.set_tokens("test-token")
        headers = await client._add_auth_header({})
        assert headers["Authorization"] == "Bearer test-token"

    @pytest.mark.asyncio
    async def test_add_auth_header_when_not_authenticated(self, client):
        """Test that no auth header is added when not authenticated."""
        headers = await client._add_auth_header({})
        assert "Authorization" not in headers


class TestAsyncHTTPClientErrorHandling:
    """Tests for error handling in AsyncHTTPClient."""

    @pytest.fixture
    def client(self):
        """Create a client for testing."""
        return AsyncHTTPClient(base_url="http://localhost:8000")

    def test_handle_401_error(self, client):
        """Test handling 401 Unauthorized."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 401
        response.json.return_value = {"detail": "Not authenticated"}
        response.text = "Not authenticated"

        with pytest.raises(AuthenticationError):
            client._handle_error_response(response)

    def test_handle_403_error(self, client):
        """Test handling 403 Forbidden."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 403
        response.json.return_value = {"detail": "Access denied"}
        response.text = "Access denied"

        with pytest.raises(AuthorizationError):
            client._handle_error_response(response)

    def test_handle_404_error(self, client):
        """Test handling 404 Not Found."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 404
        response.json.return_value = {"detail": "Not found"}
        response.text = "Not found"

        with pytest.raises(NotFoundError):
            client._handle_error_response(response)

    def test_handle_400_error(self, client):
        """Test handling 400 Bad Request."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 400
        response.json.return_value = {"detail": "Invalid request"}
        response.text = "Invalid request"

        with pytest.raises(ValidationError):
            client._handle_error_response(response)

    def test_handle_500_error(self, client):
        """Test handling 500 Internal Server Error."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 500
        response.json.return_value = {"detail": "Server error"}
        response.text = "Server error"

        with pytest.raises(ServerError):
            client._handle_error_response(response)

    def test_handle_error_with_json_parse_failure(self, client):
        """Test handling error when JSON parsing fails."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 500
        response.json.side_effect = Exception("JSON parse error")
        response.text = "Internal Server Error"

        with pytest.raises(ServerError) as exc_info:
            client._handle_error_response(response)

        assert "Internal Server Error" in str(exc_info.value)


class TestAsyncHTTPClientMethods:
    """Tests for HTTP methods in AsyncHTTPClient."""

    @pytest.fixture
    def client(self):
        """Create a client for testing."""
        return AsyncHTTPClient(base_url="http://localhost:8000")

    @pytest.mark.asyncio
    async def test_get_json(self, client):
        """Test GET request returning JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = {"id": "123", "name": "test"}

        with patch.object(client, "_request", return_value=mock_response) as mock_request:
            result = await client.get_json("/test")

        mock_request.assert_called_once()
        assert result == {"id": "123", "name": "test"}

    @pytest.mark.asyncio
    async def test_post_json(self, client):
        """Test POST request with JSON body."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.is_success = True
        mock_response.json.return_value = {"id": "new-123", "name": "created"}

        with patch.object(client, "_request", return_value=mock_response) as mock_request:
            result = await client.post_json("/test", json_data={"name": "test"})

        mock_request.assert_called_once()
        assert result["id"] == "new-123"
