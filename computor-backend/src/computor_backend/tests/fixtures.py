"""
Test fixtures for the test suite.

Provides proper database mocking and test utilities.
"""

import pytest
from typing import Generator, Dict, Any, Optional
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from computor_backend.model.base import Base
from computor_backend.permissions.principal import Principal, Claims
from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal


# Test database setup
@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create a test database session using SQLite in-memory."""
    # Create an in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# Mock database for simpler tests
@pytest.fixture
def mock_db() -> Mock:
    """Create a mock database session with common query patterns."""
    db = MagicMock(spec=Session)
    
    # Setup common query patterns
    query_mock = MagicMock()
    query_mock.filter = MagicMock(return_value=query_mock)
    query_mock.filter_by = MagicMock(return_value=query_mock)
    query_mock.join = MagicMock(return_value=query_mock)
    query_mock.outerjoin = MagicMock(return_value=query_mock)
    query_mock.order_by = MagicMock(return_value=query_mock)
    query_mock.limit = MagicMock(return_value=query_mock)
    query_mock.offset = MagicMock(return_value=query_mock)
    query_mock.first = MagicMock(return_value=None)
    query_mock.all = MagicMock(return_value=[])
    query_mock.count = MagicMock(return_value=0)
    query_mock.one_or_none = MagicMock(return_value=None)
    query_mock.scalar = MagicMock(return_value=None)
    
    # Setup subquery mock
    subquery_mock = MagicMock()
    subquery_mock.c = MagicMock()  # columns accessor
    query_mock.subquery = MagicMock(return_value=subquery_mock)
    
    db.query = MagicMock(return_value=query_mock)
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    db.rollback = MagicMock()
    db.close = MagicMock()
    
    return db


# Principal fixtures for different user types
@pytest.fixture
def admin_principal() -> Principal:
    """Create an admin Principal."""
    return Principal(
        user_id=str(uuid4()),
        is_admin=True,
        roles=["system_admin"]
    )


@pytest.fixture
def student_principal() -> Principal:
    """Create a student Principal with course role."""
    principal = Principal(
        user_id=str(uuid4()),
        is_admin=False,
        roles=["student"]
    )
    # Add course role
    claims = Claims()
    claims.dependent["course-123"] = {"_student"}
    principal.claims = claims
    return principal


@pytest.fixture
def lecturer_principal() -> Principal:
    """Create a lecturer Principal with course role."""
    principal = Principal(
        user_id=str(uuid4()),
        is_admin=False,
        roles=["lecturer"]
    )
    # Add course role
    claims = Claims()
    claims.dependent["course-123"] = {"_lecturer"}
    principal.claims = claims
    return principal


@pytest.fixture
def unauthorized_principal() -> Principal:
    """Create an unauthorized Principal."""
    return Principal(
        user_id=str(uuid4()),
        is_admin=False,
        roles=[]
    )


# Test client fixture with dependency injection
@pytest.fixture
def test_client_factory(mock_db):
    """Factory for creating test clients with different principals."""
    from fastapi.testclient import TestClient
    from computor_backend.server import app
    
    def _create_client(principal: Principal, db: Optional[Session] = None):
        """Create a test client with the given principal and database."""
        # Override dependencies
        app.dependency_overrides[get_current_principal] = lambda: principal
        if db is not None:
            app.dependency_overrides[get_db] = lambda: db
        elif mock_db is not None:
            app.dependency_overrides[get_db] = lambda: mock_db
        
        client = TestClient(app)
        
        # Clean up after use
        def cleanup():
            app.dependency_overrides.clear()
        
        client.cleanup = cleanup
        return client
    
    return _create_client


# Sample data fixtures
@pytest.fixture
def sample_organization() -> Dict[str, Any]:
    """Sample organization data."""
    return {
        "id": str(uuid4()),
        "path": "test.org",
        "properties": {
            "name": "Test Organization",
            "description": "A test organization"
        },
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }


@pytest.fixture
def sample_course() -> Dict[str, Any]:
    """Sample course data."""
    return {
        "id": str(uuid4()),
        "path": "test.org.course",
        "title": "Test Course",
        "course_family_id": str(uuid4()),
        "organization_id": str(uuid4()),
        "properties": {
            "name": "Test Course",
            "description": "A test course"
        },
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }


@pytest.fixture
def sample_course_content() -> Dict[str, Any]:
    """Sample course content data."""
    return {
        "id": str(uuid4()),
        "course_id": str(uuid4()),
        "title": "Test Assignment",
        "path": "1.basics.hello-world",
        "course_content_type_id": "assignment",
        "properties": {},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }


# Async test marker
@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for async tests."""
    import asyncio
    return asyncio.get_event_loop_policy()


# Mark async tests
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )