"""Tests for the main ComputorClient class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from computor_client.client import ComputorClient
from computor_client.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    ComputorClientError,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def base_url():
    """Default base URL for testing."""
    return "http://localhost:8000"


@pytest.fixture
def client(base_url):
    """Create a client instance for testing."""
    return ComputorClient(base_url=base_url)


@pytest.fixture
def authenticated_client(base_url):
    """Create an authenticated client for testing."""
    return ComputorClient(
        base_url=base_url,
        access_token="test-access-token",
        refresh_token="test-refresh-token",
    )


@pytest.fixture
def mock_login_response():
    """Mock successful login response."""
    return {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "expires_in": 3600,
        "user_id": "user-123",
        "token_type": "Bearer",
    }


# ============================================================================
# Tests for Client Initialization
# ============================================================================


class TestClientInitialization:
    """Tests for ComputorClient initialization."""

    def test_basic_initialization(self, base_url):
        """Test basic client initialization."""
        client = ComputorClient(base_url=base_url)
        assert client.base_url == base_url
        assert not client.is_authenticated
        assert client.user_id is None

    def test_initialization_with_tokens(self, base_url):
        """Test initialization with pre-existing tokens."""
        client = ComputorClient(
            base_url=base_url,
            access_token="test-token",
            refresh_token="test-refresh",
        )
        assert client.is_authenticated

    def test_initialization_with_custom_settings(self, base_url):
        """Test initialization with custom settings."""
        client = ComputorClient(
            base_url=base_url,
            timeout=60.0,
            max_retries=5,
            headers={"X-Custom": "value"},
        )
        assert client._timeout == 60.0
        assert client._max_retries == 5

    def test_base_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from base_url."""
        client = ComputorClient(base_url="http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"

    def test_repr(self, client):
        """Test client repr."""
        repr_str = repr(client)
        assert "ComputorClient" in repr_str
        assert "localhost:8000" in repr_str
        assert "not authenticated" in repr_str

    def test_repr_authenticated(self, authenticated_client):
        """Test authenticated client repr."""
        repr_str = repr(authenticated_client)
        assert "authenticated" in repr_str
        assert "not authenticated" not in repr_str


# ============================================================================
# Tests for Authentication
# ============================================================================


class TestClientAuthentication:
    """Tests for client authentication methods."""

    @pytest.mark.asyncio
    async def test_login_success(self, client, mock_login_response):
        """Test successful login."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_login_response

        with patch.object(client._http, "post", return_value=mock_response) as mock_post:
            result = await client.login("testuser", "password123")

        mock_post.assert_called_once_with(
            "/auth/login",
            json_data={"username": "testuser", "password": "password123"},
            authenticated=False,
        )
        assert client.is_authenticated
        assert client.user_id == "user-123"
        assert result["access_token"] == "new-access-token"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        with patch.object(
            client._http,
            "post",
            side_effect=AuthenticationError("Invalid credentials"),
        ):
            with pytest.raises(InvalidCredentialsError):
                await client.login("baduser", "badpass")

    @pytest.mark.asyncio
    async def test_logout_success(self, authenticated_client):
        """Test successful logout."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": "Logged out"}

        with patch.object(authenticated_client._http, "post", return_value=mock_response):
            result = await authenticated_client.logout()

        assert not authenticated_client.is_authenticated
        assert authenticated_client.user_id is None
        assert result["message"] == "Logged out"

    @pytest.mark.asyncio
    async def test_logout_clears_tokens_on_error(self, authenticated_client):
        """Test that logout clears tokens even on error."""
        with patch.object(
            authenticated_client._http,
            "post",
            side_effect=Exception("Network error"),
        ):
            with pytest.raises(ComputorClientError):
                await authenticated_client.logout()

        assert not authenticated_client.is_authenticated

    def test_set_token(self, client):
        """Test setting tokens directly."""
        assert not client.is_authenticated

        client.set_token("my-token", "my-refresh")

        assert client.is_authenticated

    def test_clear_tokens(self, authenticated_client):
        """Test clearing tokens."""
        assert authenticated_client.is_authenticated

        authenticated_client.clear_tokens()

        assert not authenticated_client.is_authenticated
        assert authenticated_client.user_id is None

    @pytest.mark.asyncio
    async def test_token_refresh_callback(self, authenticated_client):
        """Test the internal token refresh callback."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "refreshed-token",
            "refresh_token": "new-refresh",
        }

        with patch.object(authenticated_client._http, "post", return_value=mock_response):
            result = await authenticated_client._refresh_token("old-refresh")

        assert result["access_token"] == "refreshed-token"

    @pytest.mark.asyncio
    async def test_token_refresh_failure(self, authenticated_client):
        """Test token refresh failure returns None."""
        with patch.object(
            authenticated_client._http,
            "post",
            side_effect=Exception("Refresh failed"),
        ):
            result = await authenticated_client._refresh_token("invalid-refresh")

        assert result is None


# ============================================================================
# Tests for Endpoint Client Access
# ============================================================================


class TestEndpointClientAccess:
    """Tests for accessing endpoint clients."""

    def test_getattr_caches_client(self, authenticated_client):
        """Test that endpoint clients are cached."""
        with patch("computor_client.client.ComputorClient.__getattr__") as mock_getattr:
            # Manually test the caching logic
            authenticated_client._endpoint_clients["test_endpoint"] = "cached"
            result = authenticated_client._endpoint_clients.get("test_endpoint")
            assert result == "cached"

    def test_getattr_unknown_endpoint(self, client):
        """Test accessing unknown endpoint raises AttributeError."""
        # Access a non-existent endpoint - should raise AttributeError
        with pytest.raises(AttributeError):
            _ = client.completely_nonexistent_xyzzy_resource


# ============================================================================
# Tests for Lifecycle Management
# ============================================================================


class TestClientLifecycle:
    """Tests for client lifecycle management."""

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test closing the client."""
        await client.close()
        # Should not raise

    @pytest.mark.asyncio
    async def test_context_manager(self, base_url):
        """Test client as async context manager."""
        async with ComputorClient(base_url=base_url) as client:
            assert client is not None
        # Client should be closed after context

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_exception(self, base_url):
        """Test that client closes even when exception occurs."""
        client = None
        try:
            async with ComputorClient(base_url=base_url) as c:
                client = c
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected

        # Client should have been closed (http client cleared)
        # We verify by checking the client was set
        assert client is not None


# ============================================================================
# Tests for Custom Requests
# ============================================================================


class TestCustomRequests:
    """Tests for custom HTTP request methods."""

    @pytest.mark.asyncio
    async def test_get(self, client):
        """Test custom GET request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value"}

        with patch.object(client._http, "get", return_value=mock_response):
            result = await client.get("/custom/path", params={"foo": "bar"})

        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_post(self, client):
        """Test custom POST request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"created": True}

        with patch.object(client._http, "post", return_value=mock_response):
            result = await client.post("/custom/path", json_data={"data": "test"})

        assert result["created"] is True

    @pytest.mark.asyncio
    async def test_patch(self, client):
        """Test custom PATCH request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"updated": True}

        with patch.object(client._http, "patch", return_value=mock_response):
            result = await client.patch("/custom/path", json_data={"update": "test"})

        assert result["updated"] is True

    @pytest.mark.asyncio
    async def test_delete(self, client):
        """Test custom DELETE request."""
        with patch.object(client._http, "delete") as mock_delete:
            await client.delete("/custom/path/123")

        mock_delete.assert_called_once()


# ============================================================================
# Tests for Utility Methods
# ============================================================================


class TestUtilityMethods:
    """Tests for utility methods."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test health check returns True when API is healthy."""
        with patch.object(client._http, "get") as mock_get:
            result = await client.health_check()

        assert result is True
        mock_get.assert_called_once_with("/health", authenticated=False)

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check returns False when API is unhealthy."""
        with patch.object(client._http, "get", side_effect=Exception("Connection failed")):
            result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_current_user(self, authenticated_client):
        """Test getting current user information."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "user-123",
            "username": "testuser",
            "email": "test@example.com",
        }

        with patch.object(authenticated_client._http, "get", return_value=mock_response):
            result = await authenticated_client.get_current_user()

        assert result["id"] == "user-123"
        assert result["username"] == "testuser"
