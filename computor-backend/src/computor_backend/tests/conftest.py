"""
Pytest configuration and fixtures for all tests.
"""

import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure computor_backend is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from computor_backend.model import Base


# ---------------------------------------------------------------------------
# Reachability guards
# ---------------------------------------------------------------------------
# Some modules in this directory are integration tests wearing a unit-test
# costume: they talk to a live API, postgres or MinIO. Without a guard they fail
# with "Connection refused" on any machine that does not happen to have the
# stack up, which buries the failures that actually mean something. Skip them
# instead, and say why.

def service_available(host: str, port: int, timeout: float = 0.35) -> bool:
    """True if something is listening on host:port."""
    import socket
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def requires_service(host: str, port: int, name: str):
    """Module-level marker: skip unless host:port accepts a connection."""
    return pytest.mark.skipif(
        not service_available(host, port),
        reason=f"needs a running {name} at {host}:{port} (integration test)",
    )

# Import specific fixtures from fixtures.py to make them available to all tests
from computor_backend.tests.fixtures import (
    test_db,
    mock_db,
    admin_principal,
    student_principal,
    lecturer_principal,
    unauthorized_principal,
    test_client_factory,
    sample_organization,
    sample_course,
    sample_course_content,
    event_loop_policy
)


@pytest.fixture(scope="session")
def database_url():
    """Get database URL from environment or use default test database."""
    env_vars = {
        'POSTGRES_HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'POSTGRES_PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'POSTGRES_USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'POSTGRES_PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres_secret'),
        'POSTGRES_DB': os.environ.get('POSTGRES_DB', 'codeability')
    }
    
    return f"postgresql://{env_vars['POSTGRES_USER']}:{env_vars['POSTGRES_PASSWORD']}@{env_vars['POSTGRES_HOST']}:{env_vars['POSTGRES_PORT']}/{env_vars['POSTGRES_DB']}"


@pytest.fixture(scope="session")
def engine(database_url):
    """Create database engine (lazy — create_engine does not connect)."""
    return create_engine(database_url)


@pytest.fixture(scope="session")
def Session(engine):
    """Create session factory."""
    return sessionmaker(bind=engine)


@pytest.fixture
def session(Session):
    """Create a new database session for a test.

    Skips rather than failing with "Connection refused" when no postgres is
    running: anything asking for a real session is an integration test. Note the
    guard lives here and NOT on `engine` — the autouse setup_test_database
    fixture depends on `engine`, so skipping there skips the entire suite.
    """
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    if not service_available(host, int(port)):
        pytest.skip(f"needs a running postgres at {host}:{port} (integration test)")
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(engine):
    """Set up test database with all extensions and initial schema."""
    # Note: In a real test environment, you would:
    # 1. Create a fresh test database
    # 2. Run all migrations
    # 3. Set up test data
    # For now, we assume the database exists
    pass


# Note: pytest_configure is also defined in fixtures.py, so we don't redefine it here
# The markers are already configured there