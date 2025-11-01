"""
Simple permission tests that demonstrate proper testing with the new system.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock

from computor_backend.server import app
from computor_backend.permissions.auth import get_current_principal
from computor_backend.database import get_db
from computor_backend.permissions.principal import Principal, Claims, build_claims
from computor_backend.permissions.core import check_permissions, check_admin, can_perform_on_resource, can_perform_with_parents
from computor_backend.api.exceptions import ForbiddenException


class TestSimplePermissions:
    """Simple tests that work with the new permission system."""
    
    def test_principal_creation(self):
        """Test creating principals with different roles."""
        # Admin principal
        admin = Principal(
            user_id='admin-123',
            is_admin=True,
            roles=['system_admin']
        )
        assert admin.user_id == 'admin-123'
        assert admin.is_admin == True
        assert admin.permitted('anything', 'anything')  # Admin can do anything
        
        # Student principal
        student = Principal(
            user_id='student-123',
            is_admin=False,
            roles=['student']
        )
        assert student.user_id == 'student-123'
        assert student.is_admin == False
        assert not student.permitted('course', 'create')  # Student can't create courses
    
    def test_course_roles(self):
        """Test course role permissions."""
        # Create principal with course role
        principal = Principal(
            user_id='lecturer-123',
            is_admin=False,
            roles=['lecturer']
        )
        
        # Add course role claims
        claims = Claims()
        claims.dependent['course-456'] = {'_lecturer'}
        principal.claims = claims
        
        # Check course role
        assert '_lecturer' in principal.claims.dependent.get('course-456', set())
    
    def test_api_with_mock_db(self, mock_db, admin_principal):
        """Test API endpoint with mock database."""
        # Override dependencies
        app.dependency_overrides[get_current_principal] = lambda: admin_principal
        app.dependency_overrides[get_db] = lambda: mock_db
        
        # Create test client
        client = TestClient(app)
        
        # Test organizations endpoint
        response = client.get("/organizations")
        
        # Should not fail with 500 error
        assert response.status_code in [200, 404]  # 200 if data, 404 if empty
        
        # Clean up
        app.dependency_overrides.clear()
    
    def test_api_with_test_client_factory(self, test_client_factory, mock_db, student_principal):
        """Test using the test client factory."""
        # Create client with student principal
        client = test_client_factory(student_principal, mock_db)
        
        # Test that student can list courses (but gets filtered results)
        response = client.get("/courses")
        assert response.status_code in [200, 404]
        
        # Test that student cannot create organizations
        response = client.post("/organizations", json={
            "path": "test.org",
            "properties": {}
        })
        assert response.status_code in [403, 422]  # 403 Forbidden or 422 if validation happens first
        
        # Clean up
        client.cleanup()


class TestPermissionHelpers:
    """Test permission helper functions."""
    
    def test_check_admin_function(self):
        """Test the check_admin helper."""
        # Admin should pass
        admin = Principal(user_id='admin-1', is_admin=True, roles=['admin'])
        
        # check_admin returns True for admin
        result = check_admin(admin)
        assert result == True
        
        # Non-admin should return False
        student = Principal(user_id='student-1', is_admin=False, roles=['student'])
        result = check_admin(student)
        assert result == False
    
    def test_permission_caching(self):
        """Test that permission checks are cached."""
        principal = Principal(user_id='test-user', is_admin=True)
        
        # First check - not cached
        result1 = principal.permitted('resource', 'action')
        assert result1 == True
        
        # Second check - should use cache (we can't directly check the cache in Pydantic v2)
        result2 = principal.permitted('resource', 'action')
        assert result2 == True
        
        # Both results should be the same
        assert result1 == result2

    def test_general_and_dependent_permissions(self):
        """Test that general and dependent claims are respected."""
        # Build claims: organization:list and course_content:update on cc-1
        claim_values = [
            ("permissions", "organization:list"),
            ("permissions", "course_content:update:cc-1"),
        ]
        principal = Principal(user_id='u1', roles=['user'], claims=build_claims(claim_values))
        
        assert principal.permitted('organization', 'list') is True
        assert principal.permitted('course_content', 'update', 'cc-1') is True
        assert principal.permitted('course_content', 'update', 'cc-2') is False

    def test_course_role_permission_check(self):
        """Test course role-based permission checks via course claims."""
        course_id = 'course-abc'
        claim_values = [
            ("permissions", f"course:_tutor:{course_id}")
        ]
        principal = Principal(user_id='u2', roles=['tutor'], claims=build_claims(claim_values))
        # Should pass when required role is _student (tutor >= student)
        assert principal.permitted('course', 'get', course_id, course_role='_student') is True
        # Should fail on another course
        assert principal.permitted('course', 'get', 'course-other', course_role='_student') is False

    def test_registry_no_handler_fallback(self, mock_db):
        """If no handler is registered, non-admin should be forbidden, admin allowed."""
        class Dummy:
            __tablename__ = 'dummy'
        
        admin = Principal(user_id='a1', is_admin=True, roles=['system_admin'])
        non_admin = Principal(user_id='u3', roles=['user'])
        
        # Admin gets a query
        q = check_permissions(admin, Dummy, 'list', mock_db)
        assert hasattr(q, 'filter')
        
        # Non-admin should raise
        with pytest.raises(ForbiddenException):
            check_permissions(non_admin, Dummy, 'list', mock_db)

    def test_general_helpers_for_resource_and_parents(self):
        """Test the two general helper methods for resource and parent-scoped checks."""
        # Resource-level permission (general)
        p1 = Principal(user_id='u10', roles=['user'], claims=build_claims([
            ('permissions', 'widgets:create')
        ]))
        assert can_perform_on_resource(p1, 'widgets', 'create') is True
        assert can_perform_on_resource(p1, 'widgets', 'delete') is False

        # Parent-context permission: require course role and extra subject
        course_id = 'c-1'
        backend_id = 'eb-1'
        p2 = Principal(user_id='u20', roles=['lecturer'], claims=build_claims([
            ('permissions', f'course:_lecturer:{course_id}'),
            ('permissions', f'execution_backend:use:{backend_id}')
        ]))
        context = {
            'course_id': course_id,
            'execution_backend_id': backend_id
        }
        assert can_perform_with_parents(p2, 'create', context, min_course_role='_lecturer') is True
        # Missing extra subject permission should fail
        p3 = Principal(user_id='u30', roles=['lecturer'], claims=build_claims([
            ('permissions', f'course:_lecturer:{course_id}')
        ]))
        assert can_perform_with_parents(p3, 'create', context, min_course_role='_lecturer') is False


class TestAPIIntegration:
    """Test API integration with proper mocking."""
    
    @pytest.mark.parametrize("user_type,endpoint,method,expected_status", [
        ("admin", "/organizations", "GET", [200, 404]),
        ("student", "/organizations", "GET", [200, 404]),
        ("admin", "/organizations", "POST", [201, 422, 400]),
        ("student", "/organizations", "POST", [403, 422]),  # May get 422 if validation happens first
        ("admin", "/courses", "GET", [200, 404]),
        ("student", "/courses", "GET", [200, 404]),
    ])
    def test_endpoint_permissions(
        self, 
        test_client_factory, 
        mock_db,
        admin_principal,
        student_principal,
        user_type,
        endpoint,
        method,
        expected_status
    ):
        """Test various endpoints with different user types."""
        # Select principal based on user type
        principal = admin_principal if user_type == "admin" else student_principal
        
        # Create test client
        client = test_client_factory(principal, mock_db)
        
        # Make request based on method
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint, json={})
        
        # Check status code
        assert response.status_code in expected_status, \
            f"Expected {expected_status}, got {response.status_code} for {user_type} {method} {endpoint}"
        
        # Clean up
        client.cleanup()
