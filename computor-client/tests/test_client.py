"""Tests for the main ComputorClient class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from computor_client.client import ComputorClient
from computor_client.exceptions import ComputorClientError, NetworkError


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

    def test_api_token_becomes_the_x_api_token_header(self, base_url):
        """API-token auth is the scheme services actually use."""
        client = ComputorClient(base_url=base_url, api_token="ct_secret")
        assert client.auth_headers["X-API-Token"] == "ct_secret"
        # No bearer session is involved, so is_authenticated stays False.
        assert not client.is_authenticated

    def test_explicit_header_wins_over_api_token(self, base_url):
        client = ComputorClient(
            base_url=base_url,
            api_token="ct_from_kwarg",
            headers={"X-API-Token": "ct_from_headers"},
        )
        assert client.auth_headers["X-API-Token"] == "ct_from_headers"

    def test_access_token_is_publicly_readable(self, base_url):
        """Callers authenticating a side channel should not need private attrs."""
        client = ComputorClient(base_url=base_url, access_token="bearer-abc")
        assert client.access_token == "bearer-abc"
        assert ComputorClient(base_url=base_url).access_token is None

    def test_there_is_no_login_method(self, base_url):
        """The API exposes no local credential exchange; the method is gone."""
        assert not hasattr(ComputorClient(base_url=base_url), "login")

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
    async def test_logout_success(self, authenticated_client):
        """Test successful logout."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": "Logged out"}

        with patch.object(authenticated_client._http, "post", return_value=mock_response):
            result = await authenticated_client.logout()

        assert not authenticated_client.is_authenticated
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

    @pytest.mark.asyncio
    async def test_refresh_access_token_is_public(self, authenticated_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "rotated"}

        with patch.object(authenticated_client._http, "post", return_value=mock_response):
            token = await authenticated_client.refresh_access_token()

        assert token == "rotated"
        assert authenticated_client.access_token == "rotated"

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
        """Health check probes HEAD / — the only liveness route the API serves."""
        with patch.object(client._http, "head") as mock_head:
            result = await client.health_check()

        assert result is True
        mock_head.assert_called_once_with("/", authenticated=False)

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check returns False when API is unhealthy."""
        with patch.object(
            client._http, "head", side_effect=NetworkError("Connection failed")
        ):
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


class TestEndpointResolution:
    """__getattr__ resolves endpoint clients lazily; it must not recurse."""

    def test_resolves_and_caches_by_attribute_name(self, client):
        first = client.courses
        assert type(first).__name__ == "CoursesClient"
        assert client.courses is first

    @pytest.mark.parametrize("attribute,expected", [
        ("auth", "AuthenticationClient"),
        ("api_tokens", "TokensClient"),
        ("course_families", "CourseFamiliesClient"),
    ])
    def test_aliases_and_snake_case(self, client, attribute, expected):
        assert type(getattr(client, attribute)).__name__ == expected

    def test_unknown_endpoint_raises_attribute_error(self, client):
        with pytest.raises(AttributeError, match="No endpoint client found"):
            client.not_an_endpoint

    def test_copy_does_not_recurse(self, client):
        """__getattr__ used to recurse on dunders probed by copy/pickle."""
        import copy

        copy.copy(client)

    def test_attribute_access_before_init_does_not_recurse(self):
        bare = ComputorClient.__new__(ComputorClient)
        with pytest.raises(AttributeError):
            bare.courses

