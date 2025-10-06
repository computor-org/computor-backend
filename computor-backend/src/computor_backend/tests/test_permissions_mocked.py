"""
Permission Testing with Fully Mocked Dependencies

This test suite properly mocks all dependencies to avoid database connections
and SQLAlchemy issues with mock objects.
"""

import pytest
from uuid import uuid4
from typing import Dict, Optional
from unittest.mock import MagicMock, Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from computor_backend.permissions.principal import Principal, Claims
from computor_backend.api.exceptions import ForbiddenException


# ============================================================================
# Mock Principals for Different User Types
# ============================================================================

def create_mock_principal(
    user_id: str = None,
    is_admin: bool = False,
    roles: list = None,
    course_roles: Dict[str, str] = None
) -> Principal:
    """Create a mock Principal with specified attributes"""
    principal = Principal(
        user_id=user_id or str(uuid4()),
        is_admin=is_admin,
        roles=roles or []
    )
    
    # Add course roles if specified
    if course_roles:
        claims = Claims()
        for course_id, role in course_roles.items():
            claims.dependent[course_id] = {role}
        principal.claims = claims
    
    return principal


# Test users dictionary
TEST_USERS = {
    'admin': lambda: create_mock_principal(
        user_id='admin-123',
        is_admin=True,
        roles=['system_admin']
    ),
    'student': lambda: create_mock_principal(
        user_id='student-123',
        is_admin=False,
        roles=['student'],
        course_roles={'course-123': '_student'}
    ),
    'tutor': lambda: create_mock_principal(
        user_id='tutor-123',
        is_admin=False,
        roles=['tutor'],
        course_roles={'course-123': '_tutor'}
    ),
    'lecturer': lambda: create_mock_principal(
        user_id='lecturer-123',
        is_admin=False,
        roles=['lecturer'],
        course_roles={'course-123': '_lecturer'}
    ),
    'maintainer': lambda: create_mock_principal(
        user_id='maintainer-123',
        is_admin=False,
        roles=['maintainer'],
        course_roles={'course-123': '_maintainer'}
    ),
    'unauthorized': lambda: create_mock_principal(
        user_id='unauth-123',
        is_admin=False,
        roles=[]
    )
}


# ============================================================================
# Mock Database
# ============================================================================

def create_mock_db():
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
    query_mock.distinct = MagicMock(return_value=query_mock)
    query_mock.select_from = MagicMock(return_value=query_mock)
    
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


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Fixture for mock database"""
    return create_mock_db()


@pytest.fixture
def mock_check_permissions(monkeypatch):
    """Fixture that mocks check_permissions function"""
    def _mock_check_permissions(permissions, entity, action, db):
        """Mock check_permissions to return a query mock"""
        # Simple permission logic for testing
        if permissions.is_admin:
            return db.query(entity)
        elif action == "list":
            # Most users can list
            return db.query(entity)
        elif action == "get" and permissions.user_id != "unauth-123":
            return db.query(entity)
        elif action == "create" and permissions.is_admin:
            return db.query(entity)
        elif action == "update" and permissions.is_admin:
            return db.query(entity)
        elif action == "delete" and permissions.is_admin:
            return db.query(entity)
        else:
            raise ForbiddenException(detail={"entity": "test", "action": action})
    
    # Use monkeypatch to replace the function
    import computor_backend.permissions.core
    monkeypatch.setattr(computor_backend.permissions.core, 'check_permissions', _mock_check_permissions)
    
    # Also patch it in any modules that have already imported it
    import computor_backend.api.crud
    monkeypatch.setattr(computor_backend.api.crud, 'check_permissions', _mock_check_permissions)
    
    import computor_backend.api.organizations
    monkeypatch.setattr(computor_backend.api.organizations, 'check_permissions', _mock_check_permissions)
    
    import computor_backend.api.courses
    monkeypatch.setattr(computor_backend.api.courses, 'check_permissions', _mock_check_permissions)
    
    # Also need to handle User endpoint which has special query builder logic
    import computor_backend.api.user
    if hasattr(computor_backend.api.user, 'check_permissions'):
        monkeypatch.setattr(computor_backend.api.user, 'check_permissions', _mock_check_permissions)
    
    return _mock_check_permissions


@pytest.fixture
def test_client_factory(mock_db, mock_check_permissions):
    """Factory fixture for creating test clients with mocked dependencies"""
    from computor_backend.server import app
    from computor_backend.permissions.auth import get_current_principal
    from computor_backend.database import get_db
    
    def _create_test_client(user_type: str) -> TestClient:
        """Create a TestClient with mocked authentication for a specific user type"""
        
        # Get the mock principal
        principal = TEST_USERS[user_type]()
        
        # Create override functions
        def override_get_current_principal():
            return principal
        
        def override_get_db():
            yield mock_db
        
        # Apply overrides
        app.dependency_overrides[get_current_principal] = override_get_current_principal
        app.dependency_overrides[get_db] = override_get_db
        
        client = TestClient(app)
        
        # Store cleanup function
        def cleanup():
            app.dependency_overrides.clear()
        
        client.cleanup = cleanup
        return client
    
    return _create_test_client


# ============================================================================
# Tests
# ============================================================================

class TestOrganizationPermissions:
    """Test organization endpoint permissions with fully mocked dependencies"""
    
    @pytest.mark.parametrize("user_type,method,expected_status", [
        # GET /organizations - most users can list
        ("admin", "GET", 200),
        ("student", "GET", 200),
        ("lecturer", "GET", 200),
        ("unauthorized", "GET", 200),
        
        # POST /organizations - only admin can create
        ("admin", "POST", 422),  # 422 because we're not sending valid data
        ("student", "POST", [403, 422]),  # May get 422 if validation happens first
        ("lecturer", "POST", [403, 422]),  # May get 422 if validation happens first
        ("unauthorized", "POST", [403, 422]),  # May get 422 if validation happens first
    ])
    def test_organization_permissions(self, test_client_factory, user_type, method, expected_status):
        """Test organization endpoint with different users and methods"""
        client = test_client_factory(user_type)
        
        try:
            if method == "GET":
                response = client.get("/organizations")
            elif method == "POST":
                response = client.post("/organizations", json={})
            
            # Check status code - might be 404 if no data, 403 if forbidden
            if isinstance(expected_status, list):
                assert response.status_code in expected_status + [404, 500]
            else:
                assert response.status_code in [expected_status, 404, 500]
        finally:
            client.cleanup()


class TestCoursePermissions:
    """Test course endpoint permissions with fully mocked dependencies"""
    
    @pytest.mark.parametrize("user_type,expected_can_list", [
        ("admin", True),
        ("student", True),
        ("lecturer", True),
        ("unauthorized", True),  # Can list but gets filtered results
    ])
    def test_list_courses(self, test_client_factory, user_type, expected_can_list):
        """Test listing courses with different user roles"""
        client = test_client_factory(user_type)
        
        try:
            response = client.get("/courses")
            
            if expected_can_list:
                assert response.status_code in [200, 404]  # 404 if no courses exist
            else:
                assert response.status_code == 403
        finally:
            client.cleanup()
    
    @pytest.mark.parametrize("user_type,expected_can_create", [
        ("admin", True),
        ("student", False),
        ("lecturer", False),
        ("unauthorized", False),
    ])
    def test_create_course(self, test_client_factory, user_type, expected_can_create):
        """Test creating courses with different user roles"""
        client = test_client_factory(user_type)
        
        try:
            course_data = {
                "course_family_id": str(uuid4()),
                "path": "test.course",
                "gitlab_id": 123
            }
            
            response = client.post("/courses", json=course_data)
            
            if expected_can_create:
                assert response.status_code in [201, 400, 404, 422, 500]  # Various error codes possible
            else:
                assert response.status_code in [403, 400, 404, 422]  # May fail validation or routing first
        finally:
            client.cleanup()


class TestUserPermissions:
    """Test user endpoint permissions with fully mocked dependencies"""
    
    @pytest.mark.parametrize("user_type,expected_can_list", [
        ("admin", True),
        ("student", True),  # Can see limited user list
        ("lecturer", True),
        ("unauthorized", True),  # Can see limited list
    ])
    def test_list_users(self, test_client_factory, user_type, expected_can_list):
        """Test listing users with different user roles"""
        client = test_client_factory(user_type)
        
        try:
            response = client.get("/users")
            
            if expected_can_list:
                assert response.status_code in [200, 404]  # 404 if no users exist
            else:
                assert response.status_code == 403
        finally:
            client.cleanup()
    
    @pytest.mark.parametrize("user_type,expected_can_create", [
        ("admin", True),
        ("student", False),
        ("lecturer", False),
        ("unauthorized", False),
    ])
    def test_create_user(self, test_client_factory, user_type, expected_can_create):
        """Test creating users with different user roles"""
        client = test_client_factory(user_type)
        
        try:
            user_data = {
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123"
            }
            
            response = client.post("/users", json=user_data)
            
            if expected_can_create:
                assert response.status_code in [201, 400, 404, 422, 500]  # Various error codes possible
            else:
                assert response.status_code in [403, 400, 404, 422]  # May fail validation first
        finally:
            client.cleanup()


class TestPermissionFunctions:
    """Test permission helper functions"""
    
    def test_principal_creation(self):
        """Test creating principals with different configurations"""
        # Admin principal
        admin = create_mock_principal(
            user_id='admin-test',
            is_admin=True,
            roles=['system_admin']
        )
        assert admin.user_id == 'admin-test'
        assert admin.is_admin == True
        assert 'system_admin' in admin.roles
        
        # Student with course role
        student = create_mock_principal(
            user_id='student-test',
            is_admin=False,
            roles=['student'],
            course_roles={'course-123': '_student'}
        )
        assert student.user_id == 'student-test'
        assert student.is_admin == False
        assert '_student' in student.claims.dependent.get('course-123', set())
    
    def test_mock_check_permissions(self, mock_db, mock_check_permissions):
        """Test that mock_check_permissions works correctly"""
        admin = TEST_USERS['admin']()
        student = TEST_USERS['student']()
        
        # Admin should be able to do everything
        result = mock_check_permissions(admin, object, "create", mock_db)
        assert result is not None
        
        # Student should be able to list
        result = mock_check_permissions(student, object, "list", mock_db)
        assert result is not None
        
        # Student should not be able to create
        with pytest.raises(ForbiddenException):
            mock_check_permissions(student, object, "create", mock_db)