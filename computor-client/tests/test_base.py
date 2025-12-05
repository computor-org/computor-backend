"""Tests for base endpoint client classes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel

from computor_client.base import (
    BaseEndpointClient,
    TypedEndpointClient,
)
from computor_client.http import AsyncHTTPClient
from computor_client.exceptions import NotFoundError


# ============================================================================
# Mock Models for Testing
# ============================================================================


class MockModel(BaseModel):
    """Mock model for CRUD operations."""
    id: str
    name: str


class MockModelCreate(BaseModel):
    """Mock create model."""
    name: str


class MockModelUpdate(BaseModel):
    """Mock update model."""
    name: str


class MockModelList(BaseModel):
    """Mock list model."""
    id: str
    name: str


class MockModelQuery(BaseModel):
    """Mock query model."""
    name: str | None = None


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = AsyncMock(spec=AsyncHTTPClient)
    return client


@pytest.fixture
def typed_client(mock_http_client):
    """Create a typed endpoint client for testing."""
    return TypedEndpointClient(
        http_client=mock_http_client,
        base_path="/tests",
        response_model=MockModel,
        create_model=MockModelCreate,
        update_model=MockModelUpdate,
        list_model=MockModelList,
        query_model=MockModelQuery,
    )


# ============================================================================
# Tests for BaseEndpointClient
# ============================================================================


class TestBaseEndpointClient:
    """Tests for BaseEndpointClient."""

    def test_build_path_no_parts(self, mock_http_client):
        """Test building path with no additional parts."""
        client = TypedEndpointClient(
            http_client=mock_http_client,
            base_path="/resources",
            response_model=MockModel,
        )
        assert client._build_path() == "/resources"

    def test_build_path_with_parts(self, mock_http_client):
        """Test building path with additional parts."""
        client = TypedEndpointClient(
            http_client=mock_http_client,
            base_path="/resources",
            response_model=MockModel,
        )
        assert client._build_path("123") == "/resources/123"
        assert client._build_path("123", "action") == "/resources/123/action"

    def test_build_path_cleans_slashes(self, mock_http_client):
        """Test that path building handles extra slashes."""
        client = TypedEndpointClient(
            http_client=mock_http_client,
            base_path="/resources/",
            response_model=MockModel,
        )
        assert client._build_path("/123/") == "/resources/123"

    def test_query_to_params(self, typed_client):
        """Test converting query model to params."""
        query = MockModelQuery(name="test")
        params = typed_client._query_to_params(query)
        assert params == {"name": "test"}

    def test_query_to_params_excludes_none(self, typed_client):
        """Test that None values are excluded."""
        query = MockModelQuery(name=None)
        params = typed_client._query_to_params(query)
        assert params == {}

    def test_query_to_params_with_none_input(self, typed_client):
        """Test handling None query input."""
        params = typed_client._query_to_params(None)
        assert params is None


# ============================================================================
# Tests for TypedEndpointClient - Read Operations
# ============================================================================


class TestTypedEndpointClientRead:
    """Tests for TypedEndpointClient read operations."""

    @pytest.mark.asyncio
    async def test_get(self, typed_client, mock_http_client):
        """Test getting a single resource."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123", "name": "Test"}
        mock_http_client.get.return_value = mock_response

        result = await typed_client.get("123")

        mock_http_client.get.assert_called_once_with("/tests/123")
        assert isinstance(result, MockModel)
        assert result.id == "123"
        assert result.name == "Test"

    @pytest.mark.asyncio
    async def test_get_raw(self, typed_client, mock_http_client):
        """Test getting a resource as raw dict."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123", "name": "Test"}
        mock_http_client.get.return_value = mock_response

        result = await typed_client.get_raw("123")

        assert result == {"id": "123", "name": "Test"}

    @pytest.mark.asyncio
    async def test_list_returns_list(self, typed_client, mock_http_client):
        """Test listing resources when API returns list."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "1", "name": "First"},
            {"id": "2", "name": "Second"},
        ]
        mock_http_client.get.return_value = mock_response

        result = await typed_client.list()

        mock_http_client.get.assert_called_once_with(
            "/tests",
            params={"skip": 0, "limit": 100},
        )
        assert len(result) == 2
        assert all(isinstance(item, MockModelList) for item in result)

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, typed_client, mock_http_client):
        """Test listing with custom pagination."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_http_client.get.return_value = mock_response

        await typed_client.list(skip=10, limit=50)

        mock_http_client.get.assert_called_once_with(
            "/tests",
            params={"skip": 10, "limit": 50},
        )

    @pytest.mark.asyncio
    async def test_list_with_query(self, typed_client, mock_http_client):
        """Test listing with query parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_http_client.get.return_value = mock_response

        query = MockModelQuery(name="test")
        await typed_client.list(query=query)

        mock_http_client.get.assert_called_once_with(
            "/tests",
            params={"skip": 0, "limit": 100, "name": "test"},
        )

    @pytest.mark.asyncio
    async def test_list_handles_paginated_response(self, typed_client, mock_http_client):
        """Test listing when API returns paginated response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [{"id": "1", "name": "Item"}],
            "total": 1,
        }
        mock_http_client.get.return_value = mock_response

        result = await typed_client.list()

        assert len(result) == 1
        assert result[0].id == "1"

    @pytest.mark.asyncio
    async def test_exists_returns_true(self, typed_client, mock_http_client):
        """Test exists returns True when resource exists."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123", "name": "Test"}
        mock_http_client.get.return_value = mock_response

        result = await typed_client.exists("123")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(self, typed_client, mock_http_client):
        """Test exists returns False when resource doesn't exist."""
        mock_http_client.get.side_effect = NotFoundError("Not found")

        result = await typed_client.exists("nonexistent")

        assert result is False


# ============================================================================
# Tests for TypedEndpointClient - Write Operations
# ============================================================================


class TestTypedEndpointClientWrite:
    """Tests for TypedEndpointClient write operations."""

    @pytest.mark.asyncio
    async def test_create_with_model(self, typed_client, mock_http_client):
        """Test creating a resource with a model."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "new-123", "name": "Created"}
        mock_http_client.post.return_value = mock_response

        data = MockModelCreate(name="Created")
        result = await typed_client.create(data)

        mock_http_client.post.assert_called_once_with("/tests", json_data=data)
        assert isinstance(result, MockModel)
        assert result.id == "new-123"

    @pytest.mark.asyncio
    async def test_create_with_dict(self, typed_client, mock_http_client):
        """Test creating a resource with a dict."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "new-123", "name": "Created"}
        mock_http_client.post.return_value = mock_response

        data = {"name": "Created"}
        result = await typed_client.create(data)

        mock_http_client.post.assert_called_once_with("/tests", json_data=data)
        assert result.id == "new-123"

    @pytest.mark.asyncio
    async def test_create_raw(self, typed_client, mock_http_client):
        """Test creating a resource returning raw dict."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "new-123", "name": "Created"}
        mock_http_client.post.return_value = mock_response

        result = await typed_client.create_raw({"name": "Created"})

        assert result == {"id": "new-123", "name": "Created"}

    @pytest.mark.asyncio
    async def test_update_with_model(self, typed_client, mock_http_client):
        """Test updating a resource with a model."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123", "name": "Updated"}
        mock_http_client.patch.return_value = mock_response

        data = MockModelUpdate(name="Updated")
        result = await typed_client.update("123", data)

        mock_http_client.patch.assert_called_once_with("/tests/123", json_data=data)
        assert result.name == "Updated"

    @pytest.mark.asyncio
    async def test_update_with_dict(self, typed_client, mock_http_client):
        """Test updating a resource with a dict."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123", "name": "Updated"}
        mock_http_client.patch.return_value = mock_response

        result = await typed_client.update("123", {"name": "Updated"})

        assert result.name == "Updated"

    @pytest.mark.asyncio
    async def test_delete(self, typed_client, mock_http_client):
        """Test deleting a resource."""
        await typed_client.delete("123")

        mock_http_client.delete.assert_called_once_with("/tests/123")


# ============================================================================
# Tests for TypedEndpointClient - Convenience Methods
# ============================================================================


class TestTypedEndpointClientConvenience:
    """Tests for TypedEndpointClient convenience methods."""

    @pytest.mark.asyncio
    async def test_get_all_single_batch(self, typed_client, mock_http_client):
        """Test get_all when all items fit in one batch."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "1", "name": "First"},
            {"id": "2", "name": "Second"},
        ]
        mock_http_client.get.return_value = mock_response

        result = await typed_client.get_all(batch_size=100)

        assert len(result) == 2
        # Should only make one request since result < batch_size
        assert mock_http_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_get_all_multiple_batches(self, typed_client, mock_http_client):
        """Test get_all with multiple batches."""
        # First call returns full batch
        batch1 = [{"id": f"{i}", "name": f"Item {i}"} for i in range(10)]
        # Second call returns partial batch
        batch2 = [{"id": "10", "name": "Item 10"}]

        mock_response1 = MagicMock()
        mock_response1.json.return_value = batch1

        mock_response2 = MagicMock()
        mock_response2.json.return_value = batch2

        mock_http_client.get.side_effect = [mock_response1, mock_response2]

        result = await typed_client.get_all(batch_size=10)

        assert len(result) == 11
        assert mock_http_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_count_with_total(self, typed_client, mock_http_client):
        """Test count when API returns total."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": [], "total": 42}
        mock_http_client.get.return_value = mock_response

        result = await typed_client.count()

        assert result == 42
        mock_http_client.get.assert_called_once_with(
            "/tests",
            params={"skip": 0, "limit": 0},
        )

    @pytest.mark.asyncio
    async def test_count_fallback_to_len(self, typed_client, mock_http_client):
        """Test count falls back to len when no total."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "1"}, {"id": "2"}]
        mock_http_client.get.return_value = mock_response

        result = await typed_client.count()

        assert result == 2


# ============================================================================
# Tests for Error Cases
# ============================================================================


class TestTypedEndpointClientErrors:
    """Tests for error handling in TypedEndpointClient."""

    @pytest.mark.asyncio
    async def test_get_without_response_model(self, mock_http_client):
        """Test that get raises when no response model is configured."""
        client = TypedEndpointClient(
            http_client=mock_http_client,
            base_path="/tests",
            response_model=None,
        )

        with pytest.raises(RuntimeError, match="No response model"):
            await client.get("123")

    @pytest.mark.asyncio
    async def test_list_without_list_model(self, mock_http_client):
        """Test that list raises when no list model is configured."""
        client = TypedEndpointClient(
            http_client=mock_http_client,
            base_path="/tests",
            response_model=None,
            list_model=None,
        )

        with pytest.raises(RuntimeError, match="No list model"):
            await client.list()

    @pytest.mark.asyncio
    async def test_create_without_response_model(self, mock_http_client):
        """Test that create raises when no response model is configured."""
        client = TypedEndpointClient(
            http_client=mock_http_client,
            base_path="/tests",
            response_model=None,
        )

        with pytest.raises(RuntimeError, match="No response model"):
            await client.create({"name": "test"})
