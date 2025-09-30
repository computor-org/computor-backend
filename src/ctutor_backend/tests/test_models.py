"""
Test SQLAlchemy models and their relationships.
"""

import pytest
from ctutor_backend.model import (
    User, Account, Profile, StudentProfile, Session,
    Organization, CourseContentKind, CourseRole, CourseFamily,
    Course, CourseContentType, CourseExecutionBackend, CourseGroup,
    CourseContent, CourseMember, SubmissionGroup,
    SubmissionGroupMember, CourseMemberComment,
    ExecutionBackend, Result, Role, RoleClaim, UserRole,
    Group, GroupClaim, UserGroup, Message, MessageRead
)


@pytest.mark.unit
class TestModelImports:
    """Test that all models can be imported."""
    
    def test_auth_models(self):
        """Test auth-related model imports."""
        assert User is not None
        assert Account is not None
        assert Profile is not None
        assert StudentProfile is not None
        assert Session is not None
    
    def test_organization_models(self):
        """Test organization model imports."""
        assert Organization is not None
    
    def test_course_models(self):
        """Test course-related model imports."""
        assert CourseContentKind is not None
        assert CourseRole is not None
        assert CourseFamily is not None
        assert Course is not None
        assert CourseContentType is not None
        assert CourseExecutionBackend is not None
        assert CourseGroup is not None
        assert CourseContent is not None
        assert CourseMember is not None
        assert SubmissionGroup is not None
        assert SubmissionGroupMember is not None
        assert CourseMemberComment is not None
    
    def test_execution_models(self):
        """Test execution-related model imports."""
        assert ExecutionBackend is not None
        assert Result is not None
    
    def test_role_models(self):
        """Test role-related model imports."""
        assert Role is not None
        assert RoleClaim is not None
        assert UserRole is not None
    
    def test_group_models(self):
        """Test group-related model imports."""
        assert Group is not None
        assert GroupClaim is not None
        assert UserGroup is not None
    
    def test_message_models(self):
        """Test message-related model imports."""
        assert Message is not None
        assert MessageRead is not None


@pytest.mark.integration
class TestModelRelationships:
    """Test model relationships with database."""
    
    def test_user_relationships(self, session):
        """Test User model relationships."""
        # Query a user
        user = session.query(User).first()
        if user:
            # Test that relationships are defined
            assert hasattr(user, 'profile')
            assert hasattr(user, 'sessions')
            assert hasattr(user, 'accounts')
            assert hasattr(user, 'user_roles')
            assert hasattr(user, 'user_groups')
    
    def test_course_relationships(self, session):
        """Test Course model relationships."""
        course = session.query(Course).first()
        if course:
            # Test relationships
            assert hasattr(course, 'organization')
            assert hasattr(course, 'course_family')
            assert hasattr(course, 'course_groups')
            assert hasattr(course, 'course_members')
            assert hasattr(course, 'course_content_types')
    
    def test_organization_hierarchy(self, session):
        """Test Organization ltree hierarchy."""
        org = session.query(Organization).first()
        if org:
            assert hasattr(org, 'path')
            assert hasattr(org, 'parent_path')
            # Path should be ltree type
            assert org.path is not None
    
    def test_course_family_relationships(self, session):
        """Test CourseFamily relationships."""
        family = session.query(CourseFamily).first()
        if family:
            assert hasattr(family, 'organization')
            assert hasattr(family, 'courses')
            # Check path attribute
            assert hasattr(family, 'path')


@pytest.mark.integration
class TestDatabaseQueries:
    """Test database queries and operations."""
    
    def test_count_records(self, session):
        """Test counting records in tables."""
        user_count = session.query(User).count()
        course_count = session.query(Course).count()
        org_count = session.query(Organization).count()
        
        # Just verify queries work
        assert user_count >= 0
        assert course_count >= 0
        assert org_count >= 0
    
    def test_join_queries(self, session):
        """Test join queries between related tables."""
        # Test joining courses with organizations
        query = session.query(Course).join(Organization)
        courses_with_orgs = query.all()
        
        # Just verify the query executes
        assert isinstance(courses_with_orgs, list)