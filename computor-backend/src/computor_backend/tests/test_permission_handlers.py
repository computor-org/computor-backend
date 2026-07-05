"""
Handler-level permission tests

These tests exercise PermissionHandlers' can_perform_action and build_query
logic using lightweight principals and mocked database sessions.
"""

import pytest
from unittest.mock import MagicMock

from computor_backend.exceptions import ForbiddenException
from computor_backend.permissions.principal import Principal, build_claims
from computor_backend.permissions.handlers_impl import (
    UserPermissionHandler,
    CoursePermissionHandler,
    OrganizationPermissionHandler,
    CourseContentTypePermissionHandler,
    CourseContentPermissionHandler,
    CourseMemberPermissionHandler,
    ExamplePermissionHandler,
    ReadOnlyPermissionHandler,
)
from computor_backend.permissions.role_setup import claims_example_manager
from computor_backend.model.auth import User
from computor_backend.model.course import Course, CourseContentType, CourseMember
from computor_backend.model.example import Example, ExampleRepository


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


class TestExamplePermissionHandler:
    """Pins the read/write split introduced with the _example_manager role.

    - Admin: everything.
    - General claim holder (``_example_manager`` for authoring,
      ``_organization_manager`` for reads): allowed per-action.
    - Course ``_lecturer``: read-only (get/list/download); authoring denied.
    - tutor/student/none: nothing.
    """

    def _example_manager(self):
        # Full example-authoring claim set, exactly as the role is seeded.
        return Principal(
            user_id='em',
            roles=['_example_manager'],
            claims=build_claims(claims_example_manager()),
        )

    def _org_manager_readonly(self):
        # Mirrors claims_organization_manager()'s example portion.
        return Principal(
            user_id='om',
            roles=['_organization_manager'],
            claims=build_claims([
                ('permissions', 'example:get'),
                ('permissions', 'example:list'),
                ('permissions', 'example:download'),
                ('permissions', 'example_repository:get'),
                ('permissions', 'example_repository:list'),
            ]),
        )

    def _lecturer(self):
        return Principal(
            user_id='lec',
            roles=['user'],
            claims=build_claims([('permissions', 'course:_lecturer:c1')]),
        )

    # --- Admin ---------------------------------------------------------------
    @pytest.mark.parametrize('action', ['get', 'list', 'create', 'update', 'delete'])
    def test_admin_allowed_everything(self, action):
        handler = ExamplePermissionHandler(Example)
        admin = Principal(user_id='a', is_admin=True, roles=['_admin'])
        assert handler.can_perform_action(admin, action) is True

    # --- _example_manager ----------------------------------------------------
    @pytest.mark.parametrize('action', ['get', 'list', 'download', 'create', 'update', 'delete'])
    def test_example_manager_allowed_authoring(self, action):
        handler = ExamplePermissionHandler(Example)
        assert handler.can_perform_action(self._example_manager(), action) is True

    @pytest.mark.parametrize('action', ['get', 'list', 'create', 'update', 'delete'])
    def test_example_manager_allowed_on_repository(self, action):
        handler = ExamplePermissionHandler(ExampleRepository)
        assert handler.can_perform_action(self._example_manager(), action) is True

    # --- _organization_manager (read-only) -----------------------------------
    @pytest.mark.parametrize('action', ['get', 'list', 'download'])
    def test_org_manager_can_read(self, action):
        handler = ExamplePermissionHandler(Example)
        assert handler.can_perform_action(self._org_manager_readonly(), action) is True

    @pytest.mark.parametrize('action', ['create', 'update', 'delete', 'upload'])
    def test_org_manager_cannot_author(self, action):
        handler = ExamplePermissionHandler(Example)
        assert handler.can_perform_action(self._org_manager_readonly(), action) is False

    def test_org_manager_cannot_author_repository(self):
        handler = ExamplePermissionHandler(ExampleRepository)
        om = self._org_manager_readonly()
        assert handler.can_perform_action(om, 'get') is True
        for action in ('create', 'update', 'delete'):
            assert handler.can_perform_action(om, action) is False

    # --- course _lecturer: read-only ----------------------------------------
    @pytest.mark.parametrize('action', ['get', 'list', 'download'])
    def test_lecturer_can_read(self, action):
        handler = ExamplePermissionHandler(Example)
        assert handler.can_perform_action(self._lecturer(), action) is True

    @pytest.mark.parametrize('action', ['create', 'update', 'delete'])
    def test_lecturer_cannot_author(self, action):
        handler = ExamplePermissionHandler(Example)
        # This is the loophole the change closes: a lecturer could previously
        # create/update/delete example repositories via the CrudRouter.
        assert handler.can_perform_action(self._lecturer(), action) is False

    def test_lecturer_cannot_author_repository_build_query_raises(self):
        db = make_db()
        handler = ExamplePermissionHandler(ExampleRepository)
        with pytest.raises(ForbiddenException):
            handler.build_query(self._lecturer(), 'delete', db)

    def test_lecturer_read_build_query_returns(self):
        db = make_db()
        handler = ExamplePermissionHandler(Example)
        q = handler.build_query(self._lecturer(), 'list', db)
        assert q is db.query.return_value

    # --- tutor / student / anonymous ----------------------------------------
    @pytest.mark.parametrize('action', ['get', 'list', 'create', 'delete'])
    def test_non_lecturer_denied(self, action):
        handler = ExamplePermissionHandler(Example)
        tutor = Principal(
            user_id='tut', roles=['user'],
            claims=build_claims([('permissions', 'course:_tutor:c1')]),
        )
        assert handler.can_perform_action(tutor, action) is False
