"""
Handler-level permission tests

These tests exercise PermissionHandlers' can_perform_action and build_query
logic using lightweight principals and mocked database sessions.
"""

import pytest
from unittest.mock import MagicMock

from computor_backend.api.exceptions import ForbiddenException
from computor_backend.permissions.principal import Principal, build_claims
from computor_backend.permissions.handlers_impl import (
    UserPermissionHandler,
    CoursePermissionHandler,
    OrganizationPermissionHandler,
    CourseContentTypePermissionHandler,
    CourseContentPermissionHandler,
    CourseMemberPermissionHandler,
    ReadOnlyPermissionHandler,
)
from computor_backend.model.auth import User
from computor_backend.model.course import Course, CourseContentType, CourseMember


def make_db():
    """Create a MagicMock DB session with common methods."""
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.outerjoin.return_value = q
    q.join.return_value = q
    q.select_from.return_value = q
    q.distinct.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.offset.return_value = q
    q.all.return_value = []
    q.first.return_value = None
    q.count.return_value = 0
    q.scalar.return_value = None
    db.query.return_value = q
    return db


class TestCoursePermissionHandler:
    def test_admin_gets_all(self):
        db = make_db()
        handler = CoursePermissionHandler(Course)
        admin = Principal(user_id='a', is_admin=True, roles=['system_admin'])
        # Should simply return db.query(entity) without extra joins
        q = handler.build_query(admin, 'list', db)
        assert q is db.query.return_value

    def test_general_permission_allows(self):
        db = make_db()
        handler = CoursePermissionHandler(Course)
        resource = Course.__tablename__
        principal = Principal(
            user_id='u1',
            roles=['user'],
            claims=build_claims([('permissions', f'{resource}:list')])
        )
        q = handler.build_query(principal, 'list', db)
        assert q is db.query.return_value

    def test_filtered_query_when_no_general_permission(self, monkeypatch):
        db = make_db()
        handler = CoursePermissionHandler(Course)

        # Force filtered query builder to return a sentinel value
        sentinel = object()
        import computor_backend.permissions.query_builders as qb
        monkeypatch.setattr(qb.CoursePermissionQueryBuilder, 'build_course_filtered_query',
                            lambda entity, user_id, min_role, db_: sentinel)

        principal = Principal(user_id='u2', roles=['user'])
        q = handler.build_query(principal, 'list', db)
        assert q is sentinel


class TestCourseContentTypePermissionHandler:
    def test_write_allowed_with_lecturer_role(self):
        handler = CourseContentTypePermissionHandler(CourseContentType)
        course_id = 'c1'
        principal = Principal(
            user_id='u3',
            roles=['lecturer'],
            claims=build_claims([('permissions', f'course:_lecturer:{course_id}')])
        )
        assert handler.can_perform_action(principal, 'create') is True

    def test_list_requires_membership(self):
        db = make_db()
        handler = CourseContentTypePermissionHandler(CourseContentType)

        # First db.query(...).scalar() -> True (has membership),
        # Second db.query(...) -> return q_list
        q_membership = MagicMock()
        q_membership.scalar.return_value = True
        q_list = MagicMock()
        db.query.side_effect = [q_membership, q_list]

        principal = Principal(user_id='u4', roles=['student'])
        q = handler.build_query(principal, 'list', db)
        assert q is q_list


class TestReadOnlyPermissionHandler:
    def test_read_allowed_modify_forbidden_without_permission(self):
        from computor_backend.model.course import CourseRole
        db = make_db()
        handler = ReadOnlyPermissionHandler(CourseRole)
        principal = Principal(user_id='u5', roles=['user'])
        # Read allowed
        assert handler.build_query(principal, 'get', db) is db.query.return_value
        # Modify forbidden
        with pytest.raises(ForbiddenException):
            handler.build_query(principal, 'update', db)


class TestUserPermissionHandler:
    def test_visible_users_builder_used(self, monkeypatch):
        db = make_db()
        handler = UserPermissionHandler(User)
        # Monkeypatch the builder to return sentinel
        sentinel = object()
        import computor_backend.permissions.query_builders as qb
        monkeypatch.setattr(qb.UserPermissionQueryBuilder, 'filter_visible_users',
                            lambda user_id, db_: sentinel)
        principal = Principal(user_id='u6', roles=['user'])
        q = handler.build_query(principal, 'list', db)
        assert q is sentinel


class TestCourseMemberPermissionHandler:
    def test_get_returns_query_or_filters(self):
        db = make_db()
        handler = CourseMemberPermissionHandler(CourseMember)
        principal = Principal(user_id='u7', roles=['tutor'])
        # Should return a query-like object without raising
        q = handler.build_query(principal, 'get', db)
        assert q is not None
