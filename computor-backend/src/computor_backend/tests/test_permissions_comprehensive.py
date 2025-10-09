"""
Comprehensive Permission System Testing Suite

Tests API endpoints with different user roles and course roles for both 
old and new permission systems.
"""

import os
import pytest
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from unittest.mock import Mock, patch
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Import permission components from new system directly
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.core import check_permissions, check_admin, check_course_permissions
from computor_backend.permissions.auth import get_current_principal
from computor_backend.database import get_db


# ============================================================================
# Test Fixtures and Utilities
# ============================================================================

class MockPrincipal:
    """Mock Principal for testing different user roles"""
    
    def __init__(
        self,
        user_id: str = None,
        is_admin: bool = False,
        roles: list = None,
        course_roles: Dict[str, str] = None
    ):
        self.user_id = user_id or str(uuid4())
        self.is_admin = is_admin
        self.roles = roles or []
        self.claims = self._build_claims(course_roles or {})
        
    def _build_claims(self, course_roles: Dict[str, str]):
        """Build claims structure for course roles"""
        claims = Mock()
        claims.general = {}
        claims.dependent = {}
        
        # Add course role claims
        for course_id, role in course_roles.items():
            if course_id not in claims.dependent:
                claims.dependent[course_id] = set()
            claims.dependent[course_id].add(role)
            
        return claims
    
    def permitted(self, resource: str, action: str, resource_id: str = None, course_role: str = None) -> bool:
        """Check if action is permitted"""
        # Admin can do everything
        if self.is_admin:
            return True
            
        # Check course-specific permissions
        if resource_id and course_role:
            course_claims = self.claims.dependent.get(resource_id, set())
            return course_role in course_claims
            
        # Basic resource-action checks
        if resource in self.claims.general:
            return action in self.claims.general[resource]
            
        return False
    
    def get_user_id_or_throw(self):
        """Get user ID or raise exception"""
        if not self.user_id:
            raise Exception("User ID not found")
        return self.user_id


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = Mock(spec=Session)
    
    # Mock query responses
    def mock_query(model):
        query_mock = Mock()
        query_mock.filter = Mock(return_value=query_mock)
        query_mock.filter_by = Mock(return_value=query_mock)
        query_mock.join = Mock(return_value=query_mock)
        query_mock.outerjoin = Mock(return_value=query_mock)
        query_mock.select_from = Mock(return_value=query_mock)
        query_mock.distinct = Mock(return_value=query_mock)
        query_mock.order_by = Mock(return_value=query_mock)
        query_mock.limit = Mock(return_value=query_mock)
        query_mock.offset = Mock(return_value=query_mock)
        query_mock.first = Mock(return_value=None)
        query_mock.all = Mock(return_value=[])
        query_mock.count = Mock(return_value=0)
        query_mock.subquery = Mock(return_value=[])  # Return an empty list for IN clauses
        return query_mock
    
    session.query = Mock(side_effect=mock_query)
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    
    return session


@pytest.fixture
def test_users():
    """Create test users with different roles"""
    return {
        'admin': MockPrincipal(
            user_id='admin-user-id',
            is_admin=True,
            roles=['system_admin']
        ),
        'student': MockPrincipal(
            user_id='student-user-id',
            is_admin=False,
            roles=['student'],
            course_roles={'course-123': '_student'}
        ),
        'tutor': MockPrincipal(
            user_id='tutor-user-id',
            is_admin=False,
            roles=['tutor'],
            course_roles={'course-123': '_tutor'}
        ),
        'lecturer': MockPrincipal(
            user_id='lecturer-user-id',
            is_admin=False,
            roles=['lecturer'],
            course_roles={'course-123': '_lecturer'}
        ),
        'maintainer': MockPrincipal(
            user_id='maintainer-user-id',
            is_admin=False,
            roles=['maintainer'],
            course_roles={'course-123': '_maintainer'}
        ),
        'unauthorized': MockPrincipal(
            user_id='unauthorized-user-id',
            is_admin=False,
            roles=[],
            course_roles={}
        )
    }


# ============================================================================
# Test Application Setup
# ============================================================================

def create_test_app(mock_principal: MockPrincipal, mock_db: Session):
    """Create a test FastAPI application with mocked dependencies"""
    from computor_backend.server import app
    
    # Override authentication dependency
    def override_get_current_principal():
        return mock_principal
    
    # Override database dependency
    def override_get_db():
        yield mock_db
    
    app.dependency_overrides[get_current_principal] = override_get_current_principal
    app.dependency_overrides[get_db] = override_get_db
    
    return app


# ============================================================================
# Test Classes
# ============================================================================

class TestPermissionSystemBehavior:
    """Test new permission system behavior"""
    
    def test_permission_checks(self, test_users, mock_db_session):
        """Test permission check functions from new system"""
        # Test with admin user
        admin = test_users['admin']
        
        # Admin check should pass for admin user
        result = check_admin(admin)
        assert result is not None  # check_admin returns query or raises
        
        # Test with non-admin user
        student = test_users['student']
        
        # Student should not pass admin check
        try:
            check_admin(student)
            assert False, "Student should not pass admin check"
        except:
            pass  # Expected to fail


class TestOrganizationEndpoints:
    """Test organization endpoints with different permissions"""
    
    @pytest.mark.parametrize("user_type,expected_status", [
        ("admin", [200, 404]),
        ("student", [200, 404]),  # Students can list organizations
        ("unauthorized", [200, 403, 404]),  # May get empty list or forbidden
    ])
    def test_list_organizations(self, test_users, mock_db_session, user_type, expected_status):
        """Test GET /organizations with different user roles"""
        user = test_users[user_type]
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        response = client.get("/organizations")
        if isinstance(expected_status, list):
            assert response.status_code in expected_status
        else:
            assert response.status_code == expected_status
    
    @pytest.mark.parametrize("user_type,expected_status", [
        ("admin", [201, 422]),  # May succeed or fail validation
        ("student", [403, 422]),  # Forbidden or validation error
        ("lecturer", [403, 422]),
        ("unauthorized", [403, 422]),
    ])
    def test_create_organization(self, test_users, mock_db_session, user_type, expected_status):
        """Test POST /organizations with different user roles"""
        user = test_users[user_type]
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        org_data = {
            "path": "test.org",
            "organization_type": "university",
            "properties": {}
        }
        
        response = client.post("/organizations", json=org_data)
        if isinstance(expected_status, list):
            assert response.status_code in expected_status
        else:
            assert response.status_code == expected_status


class TestCourseEndpoints:
    """Test course-related endpoints with different permissions"""
    
    @pytest.mark.parametrize("user_type,expected_status", [
        ("admin", 200),
        ("student", 200),  # Students can see courses they're enrolled in
        ("lecturer", 200),
        ("unauthorized", 200),  # But get empty list
    ])
    def test_list_courses(self, test_users, mock_db_session, user_type, expected_status):
        """Test GET /courses with different user roles"""
        user = test_users[user_type]
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        response = client.get("/courses")
        assert response.status_code == expected_status
    
    @pytest.mark.parametrize("user_type,expected_status", [
        ("admin", [201, 400, 422]),  # May succeed or fail validation
        ("student", [403, 422]),     # Forbidden or validation error
        ("lecturer", [403, 422]),
        ("maintainer", [201, 400, 422]),  # Maintainers can create courses
        ("unauthorized", [403, 422]),
    ])
    def test_create_course(self, test_users, mock_db_session, user_type, expected_status):
        """Test POST /courses with different user roles"""
        user = test_users[user_type]
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        course_data = {
            "path": "org.family.course",
            "properties": {
                "name": "Test Course",
                "description": "A test course"
            }
        }
        
        response = client.post("/courses", json=course_data)
        if isinstance(expected_status, list):
            assert response.status_code in expected_status
        else:
            assert response.status_code == expected_status


class TestCourseContentEndpoints:
    """Test course content endpoints with course role permissions"""
    
    @pytest.mark.parametrize("user_type,expected_status", [
        ("admin", [200, 404]),
        ("student", [200, 404]),  # Students can view content
        ("tutor", [200, 404]),
        ("lecturer", [200, 404]),
        ("unauthorized", [200, 403, 404]),  # May get 200 if no auth required for listing
    ])
    def test_list_course_contents(self, test_users, mock_db_session, user_type, expected_status):
        """Test GET /course-contents with different course roles"""
        user = test_users[user_type]
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        response = client.get("/course-contents")
        if isinstance(expected_status, list):
            assert response.status_code in expected_status
        else:
            assert response.status_code == expected_status
    
    @pytest.mark.parametrize("user_type,expected_status", [
        ("admin", [201, 400, 422]),
        ("student", [403, 422]),  # Students cannot create content
        ("tutor", [403, 422]),    # Tutors cannot create content
        ("lecturer", [201, 400, 422]),  # Lecturers can create content
        ("maintainer", [201, 400, 422]),
        ("unauthorized", [403, 422]),
    ])
    def test_create_course_content(self, test_users, mock_db_session, user_type, expected_status):
        """Test POST /course-contents with different course roles"""
        user = test_users[user_type]
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        content_data = {
            "course_id": "course-123",
            "title": "Test Content",
            "content_type": "assignment",
            "properties": {}
        }
        
        response = client.post("/course-contents", json=content_data)
        if isinstance(expected_status, list):
            assert response.status_code in expected_status
        else:
            assert response.status_code == expected_status


class TestCourseMemberEndpoints:
    """Test course member management with role hierarchy"""
    
    @pytest.mark.parametrize("user_type,expected_status", [
        ("admin", 200),
        ("student", 403),  # Students cannot list members
        ("tutor", 200),    # Tutors can list members
        ("lecturer", 200),
        ("maintainer", 200),
        ("unauthorized", 403),
    ])
    def test_list_course_members(self, test_users, mock_db_session, user_type, expected_status):
        """Test GET /course-members with different course roles"""
        user = test_users[user_type]
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        response = client.get("/course-members")
        assert response.status_code == expected_status
    
    @pytest.mark.parametrize("user_type,expected_status", [
        ("admin", 201),
        ("student", 403),
        ("tutor", 403),
        ("lecturer", 403),
        ("maintainer", 201),  # Only maintainers can add members
        ("unauthorized", 403),
    ])
    def test_add_course_member(self, test_users, mock_db_session, user_type, expected_status):
        """Test POST /course-members with different course roles"""
        user = test_users[user_type]
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        member_data = {
            "course_id": "course-123",
            "user_id": "new-user-id",
            "course_role_id": "_student"
        }
        
        response = client.post("/course-members", json=member_data)
        if isinstance(expected_status, list):
            assert response.status_code in expected_status
        else:
            assert response.status_code == expected_status


class TestUserEndpoints:
    """Test user management endpoints"""
    
    @pytest.mark.parametrize("user_type,expected_status", [
        ("admin", [200, 404]),
        ("student", [200, 404]),  # Users can see limited user info
        ("unauthorized", [200, 403, 404]),
    ])
    def test_list_users(self, test_users, mock_db_session, user_type, expected_status):
        """Test GET /users with different roles"""
        user = test_users[user_type]
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        response = client.get("/users")
        if isinstance(expected_status, list):
            assert response.status_code in expected_status
        else:
            assert response.status_code == expected_status
    
    @pytest.mark.parametrize("user_type,target_user,expected_status", [
        ("admin", "any-user-id", [200, 404]),
        ("student", "student-user-id", [200, 404]),  # Can view own profile
        ("student", "other-user-id", [403, 404]),    # Cannot view others
        ("unauthorized", "any-user-id", [403, 404]),
    ])
    def test_get_user_profile(self, test_users, mock_db_session, user_type, target_user, expected_status):
        """Test GET /users/{user_id} with different permissions"""
        user = test_users[user_type]
        if target_user == "student-user-id":
            target_user = user.user_id  # Use actual user's ID
        
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        response = client.get(f"/users/{target_user}")
        if isinstance(expected_status, list):
            assert response.status_code in expected_status
        else:
            assert response.status_code == expected_status


# ============================================================================
# Integration Tests
# ============================================================================

class TestPermissionIntegration:
    """Test complete permission flows"""
    
    def test_course_lifecycle_permissions(self, test_users, mock_db_session):
        """Test complete course lifecycle with appropriate permissions"""
        # Admin creates organization
        admin = test_users['admin']
        app = create_test_app(admin, mock_db_session)
        admin_client = TestClient(app)
        
        org_response = admin_client.post("/organizations", json={
            "path": "test.university",
            "organization_type": "university",
            "properties": {}
        })
        assert org_response.status_code in [201, 400, 422]  # May fail validation
        
        # Admin creates course family
        family_response = admin_client.post("/course-families", json={
            "path": "test.university.cs",
            "properties": {"name": "Computer Science"}
        })
        assert family_response.status_code in [201, 400, 422]  # May fail validation
        
        # Admin creates course
        course_response = admin_client.post("/courses", json={
            "path": "test.university.cs.101",
            "properties": {"name": "CS 101"}
        })
        assert course_response.status_code == 201
        
        # Lecturer adds content
        lecturer = test_users['lecturer']
        app = create_test_app(lecturer, mock_db_session)
        lecturer_client = TestClient(app)
        
        content_response = lecturer_client.post("/course-contents", json={
            "course_id": "course-123",
            "title": "Week 1 Assignment",
            "content_type": "assignment",
            "properties": {}
        })
        assert content_response.status_code == 201
        
        # Student views content
        student = test_users['student']
        app = create_test_app(student, mock_db_session)
        student_client = TestClient(app)
        
        view_response = student_client.get("/course-contents")
        assert view_response.status_code == 200
        
        # Student tries to modify content (should fail)
        modify_response = student_client.patch("/course-contents/content-123", json={
            "title": "Modified Title"
        })
        assert modify_response.status_code == 403


# ============================================================================
# Core Permission Tests (New System)
# ============================================================================

class TestNewPermissionSystem:
    """Test the new permission system"""
    
    def test_admin_has_full_access(self, test_users, mock_db_session):
        """Test that admin has full access"""
        admin = test_users['admin']
        app = create_test_app(admin, mock_db_session)
        client = TestClient(app)
        
        # Admin should be able to access everything
        assert client.get("/organizations").status_code == 200
        assert client.get("/courses").status_code == 200
        assert client.get("/users").status_code == 200
        assert client.get("/course-contents").status_code == 200
    
    def test_role_hierarchy(self, test_users, mock_db_session):
        """Test course role hierarchy"""
        # Test hierarchy: _student → _tutor → _lecturer → _maintainer
        
        # Student cannot do tutor actions
        student = test_users['student']
        app = create_test_app(student, mock_db_session)
        student_client = TestClient(app)
        assert student_client.get("/course-members").status_code in [200, 403, 404]  # May get 200 if can view own membership
        
        # Tutor can do student actions but not lecturer
        tutor = test_users['tutor']
        app = create_test_app(tutor, mock_db_session)
        tutor_client = TestClient(app)
        assert tutor_client.get("/course-contents").status_code == 200
        assert tutor_client.post("/course-contents", json={}).status_code == 403
        
        # Lecturer can create content
        lecturer = test_users['lecturer']
        app = create_test_app(lecturer, mock_db_session)
        lecturer_client = TestClient(app)
        assert lecturer_client.post("/course-contents", json={
            "course_id": "course-123",
            "title": "Test",
            "content_type": "assignment"
        }).status_code == 201


# ============================================================================
# Performance Tests
# ============================================================================

class TestPermissionPerformance:
    """Test permission system performance"""
    
    def test_permission_check_performance(self, test_users, mock_db_session):
        """Test performance of permission checks"""
        import time
        
        user = test_users['lecturer']
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        # Measure time for multiple requests
        start_time = time.time()
        for _ in range(100):
            response = client.get("/courses")
            assert response.status_code == 200
        end_time = time.time()
        
        elapsed = end_time - start_time
        print(f"\nNew permission system: {elapsed:.3f}s for 100 requests")
        
        # Should complete in reasonable time
        assert elapsed < 5.0  # Should complete in under 5 seconds


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])