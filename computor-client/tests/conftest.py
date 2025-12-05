"""Pytest configuration and fixtures for computor-client tests."""

import pytest
import httpx
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from pydantic import BaseModel


# ============================================================================
# Mock Response Models
# ============================================================================


class MockUser(BaseModel):
    """Mock user model for testing."""
    id: str
    username: str
    email: str


class MockOrganization(BaseModel):
    """Mock organization model for testing."""
    id: str
    title: str
    path: str


# ============================================================================
# Mock HTTP Responses
# ============================================================================


def create_mock_response(
    status_code: int = 200,
    json_data: Optional[Any] = None,
    text: str = "",
    headers: Optional[Dict[str, str]] = None,
) -> httpx.Response:
    """Create a mock httpx.Response for testing."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.is_success = 200 <= status_code < 300
    response.text = text if text else (str(json_data) if json_data else "")
    response.headers = headers or {}

    if json_data is not None:
        response.json.return_value = json_data
    else:
        response.json.side_effect = Exception("No JSON content")

    return response


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_login_response():
    """Mock successful login response."""
    return {
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "expires_in": 3600,
        "user_id": "test-user-id",
        "token_type": "Bearer",
    }


@pytest.fixture
def mock_user_data():
    """Mock user data."""
    return {
        "id": "user-123",
        "username": "testuser",
        "email": "test@example.com",
    }


@pytest.fixture
def mock_organization_data():
    """Mock organization data."""
    return {
        "id": "org-123",
        "title": "Test Organization",
        "path": "test_org",
    }


@pytest.fixture
def mock_organizations_list():
    """Mock list of organizations."""
    return [
        {"id": "org-1", "title": "Organization 1", "path": "org_1"},
        {"id": "org-2", "title": "Organization 2", "path": "org_2"},
        {"id": "org-3", "title": "Organization 3", "path": "org_3"},
    ]


@pytest.fixture
def mock_error_response():
    """Mock error response."""
    return {
        "error_code": "AUTH_001",
        "message": "Authentication required",
        "detail": "Invalid or missing authentication token",
    }


# ============================================================================
# HTTP Client Mocking Fixtures
# ============================================================================


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx.AsyncClient."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.is_closed = False
    return client


@pytest.fixture
def base_url():
    """Default base URL for testing."""
    return "http://localhost:8000"


# ============================================================================
# respx Fixtures (if available)
# ============================================================================


@pytest.fixture
def respx_mock():
    """
    Create a respx mock context.

    This fixture is optional - tests will skip if respx is not installed.
    """
    try:
        import respx
        with respx.mock:
            yield respx
    except ImportError:
        pytest.skip("respx not installed")
