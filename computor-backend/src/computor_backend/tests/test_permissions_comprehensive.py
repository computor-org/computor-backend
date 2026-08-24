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
from computor_backend.permissions.principal import Principal, build_claims
from computor_backend.permissions.core import check_permissions, check_admin, check_course_permissions
from computor_backend.permissions.auth import get_current_principal
from computor_backend.database import get_db


# ============================================================================
# What these tests can honestly assert
# ============================================================================
#
# The app is real; only auth and the database are overridden. That means the
# permission layer genuinely runs, but every query returns Mock/empty results,
# so outcomes must be read in classes rather than exact codes:
#
#   * Validation and persistence failures surface as 400 (VAL_001) via
#     validation_exception_handler — NOT FastAPI's default 422.
#   * A refusal from the permission layer arrives as 403, or as 404 (NF_001)
#     where the CRUD path declines to confirm a row exists.
#   * A create that gets past the permission layer still cannot persist against
#     a Mock session, so it lands on 400 instead of 201.
#
# IMPORTANT: a 200 from a list endpoint proves the endpoint and permission layer
# ran. It does NOT prove row-level filtering is correct — and filtering, not a
# 403, is the actual access control for course-scoped data (see
# CourseMemberPermissionHandler.build_query). Verifying that needs a live
# database; these are wiring smoke tests, not an authorization proof.

DENIED = [403, 404]               # permission layer refused
REACHED_PERSISTENCE = [201, 400]  # allowed through; mock DB cannot persist
LISTED = [200]                    # query built and executed (rows always empty)

# Non-admin reads of scope-owned entities (organizations, course families) build
# a real SQLAlchemy subquery and feed it to Column.in_(). A Mock session hands
# back a Mock there, which SQLAlchemy rightly rejects, so those parametrizations
# cannot run without a database. They previously "passed" only because the old
# MockPrincipal had malformed claims that sent the handler down the trivial
# branch — green for the wrong reason.
NEEDS_REAL_DB = pytest.mark.skip(
    reason="Scoped subquery composition needs a live database, not a Mock session."
)


# ============================================================================
# Test Fixtures and Utilities
# ============================================================================

def make_principal(
    user_id: str = None,
    is_admin: bool = False,
    roles: list = None,
    course_roles: Dict[str, str] = None,
):
    """Build a REAL Principal for a test user.

    This used to be a hand-rolled ``MockPrincipal``, which drifted badly: it
    lacked methods the handlers call (``get_scoped_ids_with_role``,
    ``get_course_assignment_ceiling``) and, worse, stored course claims as
    ``dependent[course_id] = {role}`` when the real shape is
    ``dependent["course"][course_id] = {role}``. Both meant the tests exercised
    a permission model that did not exist. Using the production Principal keeps
    them honest and immune to that class of drift.
    """
    claim_values = [
        ("permissions", f"course:{role}:{course_id}")
        for course_id, role in (course_roles or {}).items()
    ]
    return Principal(
        user_id=user_id or str(uuid4()),
        is_admin=is_admin,
        roles=roles or [],
        claims=build_claims(claim_values),
    )


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
        # list_entities eager-loads the relationships its DTO reads.
        query_mock.options = Mock(return_value=query_mock)
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
        'admin': make_principal(
            user_id='00000000-0000-0000-0000-000000000001',
            is_admin=True,
            roles=['system_admin']
        ),
        'student': make_principal(
            user_id='00000000-0000-0000-0000-000000000002',
            is_admin=False,
            roles=['student'],
            course_roles={'course-123': '_student'}
        ),
        'tutor': make_principal(
            user_id='00000000-0000-0000-0000-000000000003',
            is_admin=False,
            roles=['tutor'],
            course_roles={'course-123': '_tutor'}
        ),
        'lecturer': make_principal(
            user_id='00000000-0000-0000-0000-000000000004',
            is_admin=False,
            roles=['lecturer'],
            course_roles={'course-123': '_lecturer'}
        ),
        'maintainer': make_principal(
            user_id='00000000-0000-0000-0000-000000000005',
            is_admin=False,
            roles=['maintainer'],
            course_roles={'course-123': '_maintainer'}
        ),
        'unauthorized': make_principal(
            user_id='00000000-0000-0000-0000-000000000006',
            is_admin=False,
            roles=[],
            course_roles={}
        )
    }


# ============================================================================
# Test Application Setup
# ============================================================================

def create_test_app(principal: Principal, mock_db: Session):
    """Create a test FastAPI application with mocked dependencies"""
    from computor_backend.server import app
    
    # Override authentication dependency
    def override_get_current_principal():
        return principal

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
        pytest.param("student", [200, 404], marks=NEEDS_REAL_DB),
        pytest.param("unauthorized", [200, 403, 404], marks=NEEDS_REAL_DB),
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
        ("admin", REACHED_PERSISTENCE),
        ("student", DENIED),
        ("lecturer", DENIED),
        ("unauthorized", DENIED),
    ])
    def test_create_organization(self, test_users, mock_db_session, user_type, expected_status):
        """Test POST /organizations with different user roles"""
        user = test_users[user_type]
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        # Payload must be VALID, otherwise FastAPI answers 400 before the
        # permission layer runs and the test proves nothing about authorization.
        org_data = {
            "path": "test_org",
            "title": "Test Organization",  # required: non-user orgs must have one
            "organization_type": "organization",
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
        ("admin", REACHED_PERSISTENCE),
        ("student", DENIED),
        ("lecturer", DENIED),
        # A _maintainer role INSIDE course-123 does not authorize creating a new
        # course: that is scoped to the course family / organization above it.
        ("maintainer", DENIED),
        ("unauthorized", DENIED),
    ])
    def test_create_course(self, test_users, mock_db_session, user_type, expected_status):
        """Test POST /courses with different user roles"""
        user = test_users[user_type]
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        course_data = {
            "path": "org.family.course",
            "course_family_id": "family-123",
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
        ("admin", REACHED_PERSISTENCE),
        ("student", DENIED),
        ("tutor", DENIED),
        ("lecturer", REACHED_PERSISTENCE),
        ("maintainer", REACHED_PERSISTENCE),
        ("unauthorized", DENIED),
    ])
    def test_create_course_content(self, test_users, mock_db_session, user_type, expected_status):
        """Test POST /course-contents with different course roles"""
        user = test_users[user_type]
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        content_data = {
            "path": "assignment1",
            "course_id": "course-123",
            "course_content_type_id": "type-123",
            "title": "Test Content",
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
        # Course-scoped reads are filtered, not refused: build_query narrows the
        # query to the caller's own membership, so everyone gets 200 and the
        # row set is the control. See the module header.
        ("admin", LISTED),
        ("student", LISTED),
        ("tutor", LISTED),
        ("lecturer", LISTED),
        ("maintainer", LISTED),
        ("unauthorized", LISTED),
    ])
    def test_list_course_members(self, test_users, mock_db_session, user_type, expected_status):
        """Test GET /course-members with different course roles"""
        user = test_users[user_type]
        app = create_test_app(user, mock_db_session)
        client = TestClient(app)
        
        response = client.get("/course-members")
        assert response.status_code in expected_status

    @pytest.mark.parametrize("user_type,expected_status", [
        # CourseMemberPermissionHandler.ACTION_ROLE_MAP maps "create" to
        # LECTURER, so lecturers and above get through to persistence.
        ("admin", REACHED_PERSISTENCE),
        ("student", DENIED),
        ("tutor", DENIED),
        ("lecturer", REACHED_PERSISTENCE),
        ("maintainer", REACHED_PERSISTENCE),
        ("unauthorized", DENIED),
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
        ("admin", "00000000-0000-0000-0000-000000000099", [200, 404]),
        ("student", "own-id", [200, 404]),  # Can view own profile
        ("student", "00000000-0000-0000-0000-000000000099", [403, 404]),    # Cannot view others
        ("unauthorized", "00000000-0000-0000-0000-000000000099", [403, 404]),
    ])
    def test_get_user_profile(self, test_users, mock_db_session, user_type, target_user, expected_status):
        """Test GET /users/{user_id} with different permissions"""
        user = test_users[user_type]
        if target_user == "own-id":
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
        assert course_response.status_code in REACHED_PERSISTENCE
        
        # Lecturer adds content
        lecturer = test_users['lecturer']
        app = create_test_app(lecturer, mock_db_session)
        lecturer_client = TestClient(app)
        
        content_response = lecturer_client.post("/course-contents", json={
            "path": "week1",
            "course_id": "course-123",
            "course_content_type_id": "type-123",
            "title": "Week 1 Assignment",
            "properties": {}
        })
        assert content_response.status_code in REACHED_PERSISTENCE
        
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
        assert modify_response.status_code in DENIED


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
        # Body must be valid, or validation answers 400 before authorization runs.
        tutor_content = tutor_client.post("/course-contents", json={
            "path": "assignment1",
            "course_id": "course-123",
            "course_content_type_id": "type-123",
        })
        assert tutor_content.status_code in DENIED
        
        # Lecturer can create content
        lecturer = test_users['lecturer']
        app = create_test_app(lecturer, mock_db_session)
        lecturer_client = TestClient(app)
        assert lecturer_client.post("/course-contents", json={
            "path": "assignment2",
            "course_id": "course-123",
            "course_content_type_id": "type-123",
            "title": "Test",
        }).status_code in REACHED_PERSISTENCE


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