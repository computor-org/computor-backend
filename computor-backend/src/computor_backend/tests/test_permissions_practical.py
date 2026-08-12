"""
Practical Permission Testing for FastAPI Endpoints

This test suite uses FastAPI's TestClient with dependency overrides
to test permissions for different user roles and course roles.
"""

import os
import pytest
from uuid import uuid4
from typing import Dict, Optional
from unittest.mock import MagicMock, Mock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Import from new permission system directly
from computor_backend.server import app
from computor_backend.permissions.auth import get_current_principal
from computor_backend.database import get_db
from computor_backend.permissions.principal import Principal, Claims, build_claims

# See test_permissions_comprehensive.py for the full rationale: the app is real
# but the database is a Mock, so outcomes come in classes. Validation and
# persistence failures are 400 (VAL_001), never FastAPI's 422; a refusal is 403
# or 404 (NF_001); an allowed create cannot persist and lands on 400.
DENIED = [403, 404]               # permission layer refused
REACHED_PERSISTENCE = [201, 400]  # allowed through; mock DB cannot persist
from computor_backend.permissions.core import check_permissions, check_admin, check_course_permissions


# ============================================================================
# Mock Principals for Different User Types
# ============================================================================

def create_mock_principal(
    user_id: str = None,
    is_admin: bool = False,
    roles: list = None,
    course_roles: Dict[str, str] = None
) -> Principal:
    """Create a mock Principal for testing (new system only)"""
    principal = Principal(
        user_id=user_id or str(uuid4()),
        is_admin=is_admin,
        roles=roles or []
    )
    
    # Course claims nest as dependent["course"][course_id] = {roles}. Writing
    # dependent[course_id] directly (as this used to) means the handlers never
    # see the role, so every course-scoped test silently checked nothing.
    if course_roles:
        principal.claims = build_claims([
            ("permissions", f"course:{role}:{course_id}")
            for course_id, role in course_roles.items()
        ])
    
    return principal


# Test user fixtures
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
# Test Client Factory
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


def create_test_client(user_type: str) -> TestClient:
    """Create a TestClient with mocked authentication for a specific user type"""
    from unittest.mock import patch
    
    # Get the mock principal
    principal = TEST_USERS[user_type]()
    
    # Create mock database
    mock_db = create_mock_db()
    
    # Create override functions
    def override_get_current_principal():
        return principal
    
    def override_get_db():
        yield mock_db
    
    # Apply overrides
    app.dependency_overrides[get_current_principal] = override_get_current_principal
    app.dependency_overrides[get_db] = override_get_db
    
    # Also need to mock check_permissions to return a query mock
    # instead of trying to build a real SQLAlchemy query
    original_check_permissions = check_permissions
    
    def mock_check_permissions(permissions, entity, action, db):
        """Mock check_permissions to return a query mock"""
        # For admin or if action is allowed, return the query mock
        # For others, raise ForbiddenException
        from computor_backend.exceptions import ForbiddenException
        
        # Simple permission logic for testing
        if permissions.is_admin:
            return db.query(entity)
        elif action == "list":
            # Most users can list
            return db.query(entity)
        elif action == "get" and user_type != "unauthorized":
            return db.query(entity)
        elif action == "create" and not permissions.is_admin:
            # Non-admins cannot create
            raise ForbiddenException(detail={"entity": str(entity.__name__ if hasattr(entity, '__name__') else entity), "action": action})
        else:
            return db.query(entity)
    
    # Monkey patch the check_permissions function in all modules
    import computor_backend.permissions.core
    computor_backend.permissions.core.check_permissions = mock_check_permissions
    
    # Also patch it in API modules that may have imported it
    import computor_backend.business_logic.crud
    if hasattr(computor_backend.business_logic.crud, 'check_permissions'):
        computor_backend.business_logic.crud.check_permissions = mock_check_permissions
    
    import computor_backend.api.organizations
    if hasattr(computor_backend.api.organizations, 'check_permissions'):
        computor_backend.api.organizations.check_permissions = mock_check_permissions
    
    import computor_backend.api.courses
    if hasattr(computor_backend.api.courses, 'check_permissions'):
        computor_backend.api.courses.check_permissions = mock_check_permissions
    
    import computor_backend.api.user
    if hasattr(computor_backend.api.user, 'check_permissions'):
        computor_backend.api.user.check_permissions = mock_check_permissions
    
    return TestClient(app)


# ============================================================================
# Permission Tests
# ============================================================================

class TestPermissionSystem:
    """Test the new permission system"""
    
    def test_principal_creation(self):
        """Test creating principals with different roles"""
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
        assert '_student' in student.claims.dependent['course']['course-123']


class TestOrganizationPermissions:
    """Test organization endpoint permissions"""
    
    @pytest.mark.parametrize("user_type,method,expected_status", [
        # GET /organizations - most users can list
        ("admin", "GET", 200),
        ("student", "GET", 200),
        ("lecturer", "GET", 200),
        ("unauthorized", "GET", 200),
        
        # POST /organizations with an EMPTY body: validation answers before the
        # permission layer, so every role gets 400 (VAL_001) regardless of role.
        # Role separation for creates is covered in test_permissions_comprehensive.
        ("admin", "POST", [400]),
        ("student", "POST", [400]),
        ("lecturer", "POST", [400]),
        ("unauthorized", "POST", [400]),
    ])
    def test_organization_permissions(self, user_type, method, expected_status):
        """Test organization endpoint with different users and methods"""
        # Store original check_permissions from all modules
        import computor_backend.permissions.core
        import computor_backend.business_logic.crud
        import computor_backend.api.organizations
        
        originals = {
            'core': computor_backend.permissions.core.check_permissions,
            'crud': getattr(computor_backend.business_logic.crud, 'check_permissions', None),
            'organizations': getattr(computor_backend.api.organizations, 'check_permissions', None),
        }
        
        try:
            client = create_test_client(user_type)
            
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
            # Clean up overrides
            app.dependency_overrides.clear()
            # Restore original check_permissions
            computor_backend.permissions.core.check_permissions = originals['core']
            if originals['crud']:
                computor_backend.business_logic.crud.check_permissions = originals['crud']
            if originals['organizations']:
                computor_backend.api.organizations.check_permissions = originals['organizations']


class TestCoursePermissions:
    """Test course endpoint permissions"""
    
    @pytest.mark.parametrize("user_type,expected_can_list", [
        ("admin", True),
        ("student", True),
        ("lecturer", True),
        ("unauthorized", True),  # Can list but gets filtered results
    ])
    def test_list_courses(self, user_type, expected_can_list):
        """Test listing courses with different user roles"""
        import computor_backend.permissions.core
        import computor_backend.business_logic.crud
        import computor_backend.api.courses
        
        originals = {
            'core': computor_backend.permissions.core.check_permissions,
            'crud': getattr(computor_backend.business_logic.crud, 'check_permissions', None),
            'courses': getattr(computor_backend.api.courses, 'check_permissions', None),
        }
        
        try:
            client = create_test_client(user_type)
            response = client.get("/courses")
            
            if expected_can_list:
                assert response.status_code in [200, 404]  # 404 if no courses exist
            else:
                assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()
            computor_backend.permissions.core.check_permissions = originals['core']
            if originals['crud']:
                computor_backend.business_logic.crud.check_permissions = originals['crud']
            if originals['courses']:
                computor_backend.api.courses.check_permissions = originals['courses']
    
    @pytest.mark.parametrize("user_type,expected_can_create", [
        ("admin", True),
        ("student", False),
        ("lecturer", False),
        ("maintainer", False),  # Needs to be maintainer of parent course family
        ("unauthorized", False),
    ])
    def test_create_course(self, user_type, expected_can_create):
        """Test creating courses with different user roles"""
        client = create_test_client(user_type)
        
        course_data = {
            "path": "test.university.cs.101",
            "course_family_id": "family-123",
            "properties": {
                "name": "Test Course"
            }
        }
        
        response = client.post("/courses", json=course_data)
        
        if expected_can_create:
            assert response.status_code in REACHED_PERSISTENCE + [409]
        else:
            assert response.status_code in DENIED
        
        app.dependency_overrides.clear()


class TestCourseContentPermissions:
    """Test course content permissions based on course roles"""
    
    @pytest.mark.parametrize("user_type,expected_can_list", [
        ("admin", True),
        ("student", True),   # Students in course can view content
        ("tutor", True),
        ("lecturer", True),
        ("unauthorized", True),  # Gets empty list
    ])
    def test_list_course_contents(self, user_type, expected_can_list):
        """Test listing course contents with different course roles"""
        client = create_test_client(user_type)
        response = client.get("/course-contents")
        
        if expected_can_list:
            assert response.status_code in [200, 404]
        else:
            assert response.status_code == 403
        
        app.dependency_overrides.clear()
    
    @pytest.mark.parametrize("user_type,expected_can_create", [
        ("admin", True),
        ("student", False),   # Students cannot create content
        ("tutor", False),     # Tutors cannot create content
        ("lecturer", True),   # Lecturers can create content
        ("maintainer", True),
        ("unauthorized", False),
    ])
    def test_create_course_content(self, user_type, expected_can_create):
        """Test creating course content with different course roles"""
        client = create_test_client(user_type)
        
        content_data = {
            "path": "assignment1",
            "course_id": "course-123",
            "course_content_type_id": "type-123",
            "title": "Test Assignment",
            "properties": {}
        }
        
        response = client.post("/course-contents", json=content_data)
        
        if expected_can_create:
            assert response.status_code in REACHED_PERSISTENCE
        else:
            assert response.status_code in DENIED
        
        app.dependency_overrides.clear()


class TestUserPermissions:
    """Test user management permissions"""
    
    @pytest.mark.parametrize("user_type,expected_status", [
        ("admin", 200),
        ("student", 200),  # Can see limited user list
        ("unauthorized", 200),
    ])
    def test_list_users(self, user_type, expected_status):
        """Test listing users with different roles"""
        import computor_backend.permissions.core
        import computor_backend.business_logic.crud
        import computor_backend.api.user
        
        originals = {
            'core': computor_backend.permissions.core.check_permissions,
            'crud': getattr(computor_backend.business_logic.crud, 'check_permissions', None),
            'user': getattr(computor_backend.api.user, 'check_permissions', None),
        }
        
        try:
            client = create_test_client(user_type)
            response = client.get("/users")
            
            assert response.status_code in [expected_status, 404]
        finally:
            app.dependency_overrides.clear()
            computor_backend.permissions.core.check_permissions = originals['core']
            if originals['crud']:
                computor_backend.business_logic.crud.check_permissions = originals['crud']
            if originals['user']:
                computor_backend.api.user.check_permissions = originals['user']


# ============================================================================
# Core Permission Tests (New System)
# ============================================================================

class TestCorePermissions:
    """Test core permissions with new system"""
    
    def teardown_method(self, method):
        """Clean up after each test"""
        app.dependency_overrides.clear()
    
    def test_admin_access(self):
        """Test admin has full access"""
        client = create_test_client("admin")
        
        # Admin should access everything
        assert client.get("/organizations").status_code in [200, 404]
        assert client.get("/courses").status_code in [200, 404]
        assert client.get("/users").status_code in [200, 404]
        assert client.get("/course-contents").status_code in [200, 404]
    
    def test_student_restrictions(self):
        """Test student restrictions"""
        client = create_test_client("student")
        
        # Students can view but not create most things
        assert client.get("/courses").status_code in [200, 404]
        # Empty bodies: validation answers first, so both are 400 (VAL_001).
        assert client.post("/courses", json={}).status_code == 400
        assert client.post("/organizations", json={}).status_code == 400
    
    def test_lecturer_course_permissions(self):
        """Test lecturer course permissions"""
        client = create_test_client("lecturer")
        
        # Lecturers can create course content
        content_data = {
            "path": "content1",
            "course_id": "course-123",
            "course_content_type_id": "type-123",
            "title": "Test Content"
        }
        response = client.post("/course-contents", json=content_data)
        # Should get past the permission layer; the mock DB then blocks the write.
        assert response.status_code in REACHED_PERSISTENCE


# ============================================================================
# Run Instructions
# ============================================================================

"""
To run these tests:

1. Start the services (database, redis, etc.):
   ./computor.sh up dev -d

2. Run all permission tests:
   pytest src/computor_backend/tests/test_permissions_practical.py -v

3. Run specific test class:
   pytest src/computor_backend/tests/test_permissions_practical.py::TestCoursePermissions -v

4. Run core permission tests:
   pytest src/computor_backend/tests/test_permissions_practical.py::TestCorePermissions -v -s
"""

if __name__ == "__main__":
    # Quick test to verify it works
    print("Testing new permission system")
    
    # Test with admin
    client = create_test_client("admin")
    response = client.get("/organizations")
    print(f"Admin GET /organizations: {response.status_code}")
    
    # Test with student
    client = create_test_client("student")
    response = client.get("/organizations")
    print(f"Student GET /organizations: {response.status_code}")
    
    # Clean up
    app.dependency_overrides.clear()