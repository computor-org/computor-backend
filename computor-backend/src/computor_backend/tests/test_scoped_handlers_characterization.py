"""Characterization tests for the scoped-entity permission handlers.

These tests PIN the exact observable behaviour of
``OrganizationPermissionHandler`` and ``CourseFamilyPermissionHandler``
before/after the TASK-109 refactor that merges the two near-verbatim
clones behind a shared ``_ScopedEntityPermissionHandler`` base.

They must pass UNCHANGED on the pre-refactor baseline and again on the
refactored code. Because the two handlers are meant to be identical
except for (a) their scope name, (b) the ``Course`` FK column they
cascade through, and (c) their role-map, the SAME matrix is driven
against BOTH handlers via parametrization.

``can_perform_action`` is a pure claim/role decision and needs no DB.
``build_query`` is exercised with a lightweight recording fake session
(no live DB): ``user_courses_subquery`` builds a plain ``select()``
without touching the session, and every ``db.query(...)`` result is a
chainable empty list, so ``.in_(...)`` coercions stay well-defined.
This lets us assert which ``Course`` FK column each scope cascades
through (``organization_id`` vs ``course_family_id``) by identity.
"""

import pytest

from computor_backend.exceptions import ForbiddenException
from computor_backend.permissions.principal import Principal, build_claims
from computor_backend.permissions.handlers_impl import (
    OrganizationPermissionHandler,
    CourseFamilyPermissionHandler,
)
from computor_backend.model.course import Course, CourseFamily
from computor_backend.model.organization import Organization


# ---------------------------------------------------------------------------
# Recording fake session
# ---------------------------------------------------------------------------
class _FakeQ(list):
    """A chainable query stand-in.

    Subclasses ``list`` so it is a real (empty) iterable that
    ``ColumnOperators.in_`` accepts as an empty IN-list, while also
    exposing the chaining methods the handlers call. Every chaining
    method returns ``self`` so ``db.query(...).filter(...)`` never
    yields a ``MagicMock`` that would break ``.in_()`` coercion.
    """

    def filter(self, *a, **k):
        return self

    def join(self, *a, **k):
        return self

    def outerjoin(self, *a, **k):
        return self

    def select_from(self, *a, **k):
        return self

    def scalar(self):
        return None

    def first(self):
        return None

    def all(self):
        return []


class _RecordingDB:
    """Fake session that records the positional args of each ``query``."""

    def __init__(self):
        self.query_calls = []

    def query(self, *args):
        self.query_calls.append(args)
        return _FakeQ()

    def queried(self, column) -> bool:
        """True if some ``db.query(col, ...)`` used ``column`` (by identity)."""
        return any(
            any(arg is column for arg in call) for call in self.query_calls
        )


# ---------------------------------------------------------------------------
# Scope matrix: (label, HandlerClass, entity, scope_claim_key,
#                this_scope_course_fk, other_scope_course_fk)
# ---------------------------------------------------------------------------
SCOPES = [
    (
        "organization",
        OrganizationPermissionHandler,
        Organization,
        "organization",
        Course.organization_id,
        Course.course_family_id,
    ),
    (
        "course_family",
        CourseFamilyPermissionHandler,
        CourseFamily,
        "course_family",
        Course.course_family_id,
        Course.organization_id,
    ),
]

ALL_ACTIONS = ["get", "list", "create", "update", "archive", "delete"]
WRITE_ACTIONS = ["create", "update", "archive", "delete"]

# Minimum scoped role required per write action (mirrors ACTION_*_ROLE_MAP).
WRITE_MIN_ROLE = {"update": "_developer", "archive": "_owner", "delete": "_owner"}


def _pid(cfg):
    return cfg[0]


# ---------------------------------------------------------------------------
# Principal builders
# ---------------------------------------------------------------------------
def _admin():
    return Principal(user_id="admin", is_admin=True, roles=["_admin"])


def _general(handler, actions=ALL_ACTIONS):
    """Holder of the general ``<tablename>:<action>`` claim for all actions."""
    res = handler.resource_name
    return Principal(
        user_id="gen",
        roles=["user"],
        claims=build_claims([("permissions", f"{res}:{a}") for a in actions]),
    )


def _scoped(scope_key, role, scope_id="S1"):
    """Holder of a single scoped role (``organization``/``course_family``)."""
    return Principal(
        user_id="scoped",
        roles=["user"],
        claims=build_claims([("permissions", f"{scope_key}:{role}:{scope_id}")]),
    )


def _no_access():
    return Principal(user_id="none", roles=["user"])


# ===========================================================================
# can_perform_action matrix
# ===========================================================================
class TestCanPerformAction:
    @pytest.mark.parametrize("cfg", SCOPES, ids=_pid)
    @pytest.mark.parametrize("action", ALL_ACTIONS)
    def test_admin_allowed_everything(self, cfg, action):
        _, HandlerCls, entity, *_ = cfg
        handler = HandlerCls(entity)
        assert handler.can_perform_action(_admin(), action, resource_id="S1") is True

    @pytest.mark.parametrize("cfg", SCOPES, ids=_pid)
    @pytest.mark.parametrize("action", ALL_ACTIONS)
    def test_general_permission_allows_matching_action(self, cfg, action):
        _, HandlerCls, entity, *_ = cfg
        handler = HandlerCls(entity)
        # A general claim exists for every action → each action is allowed.
        assert handler.can_perform_action(_general(handler), action) is True

    @pytest.mark.parametrize("cfg", SCOPES, ids=_pid)
    def test_general_permission_is_action_specific(self, cfg):
        _, HandlerCls, entity, *_ = cfg
        handler = HandlerCls(entity)
        # Only the ``delete`` general claim is held.
        p = _general(handler, actions=["delete"])
        assert handler.can_perform_action(p, "delete") is True
        # ``update`` with no resource_id and no scoped role → denied.
        assert handler.can_perform_action(p, "update") is False

    @pytest.mark.parametrize("cfg", SCOPES, ids=_pid)
    def test_no_access_reads_true_writes_false(self, cfg):
        _, HandlerCls, entity, *_ = cfg
        handler = HandlerCls(entity)
        p = _no_access()
        # get/list always return True at the gate (build_query filters).
        assert handler.can_perform_action(p, "get") is True
        assert handler.can_perform_action(p, "list") is True
        # writes denied, both with and without a resource_id.
        for action in WRITE_ACTIONS:
            assert handler.can_perform_action(p, action) is False
            assert handler.can_perform_action(p, action, resource_id="S1") is False

    @pytest.mark.parametrize("cfg", SCOPES, ids=_pid)
    def test_scoped_developer(self, cfg):
        _, HandlerCls, entity, scope_key, *_ = cfg
        handler = HandlerCls(entity)
        p = _scoped(scope_key, "_developer", scope_id="S1")
        # reads always allowed
        assert handler.can_perform_action(p, "get") is True
        assert handler.can_perform_action(p, "list") is True
        # update requires _developer → allowed on the held scope
        assert handler.can_perform_action(p, "update", resource_id="S1") is True
        # archive/delete require _owner → denied for a developer
        assert handler.can_perform_action(p, "archive", resource_id="S1") is False
        assert handler.can_perform_action(p, "delete", resource_id="S1") is False
        # a different scope id → no role there → denied
        assert handler.can_perform_action(p, "update", resource_id="S2") is False
        # write without resource_id → denied (scoped roles need a target)
        assert handler.can_perform_action(p, "update", resource_id=None) is False
        # create is not in the role map → denied
        assert handler.can_perform_action(p, "create", resource_id="S1") is False

    @pytest.mark.parametrize("cfg", SCOPES, ids=_pid)
    def test_scoped_manager(self, cfg):
        _, HandlerCls, entity, scope_key, *_ = cfg
        handler = HandlerCls(entity)
        p = _scoped(scope_key, "_manager", scope_id="S1")
        # _manager satisfies _developer → update allowed
        assert handler.can_perform_action(p, "update", resource_id="S1") is True
        # _manager does not satisfy _owner → archive/delete denied
        assert handler.can_perform_action(p, "archive", resource_id="S1") is False
        assert handler.can_perform_action(p, "delete", resource_id="S1") is False

    @pytest.mark.parametrize("cfg", SCOPES, ids=_pid)
    def test_scoped_owner(self, cfg):
        _, HandlerCls, entity, scope_key, *_ = cfg
        handler = HandlerCls(entity)
        p = _scoped(scope_key, "_owner", scope_id="S1")
        assert handler.can_perform_action(p, "update", resource_id="S1") is True
        assert handler.can_perform_action(p, "archive", resource_id="S1") is True
        assert handler.can_perform_action(p, "delete", resource_id="S1") is True
        # still needs a target and is not granted create
        assert handler.can_perform_action(p, "update", resource_id=None) is False
        assert handler.can_perform_action(p, "create", resource_id="S1") is False

    @pytest.mark.parametrize("cfg", SCOPES, ids=_pid)
    def test_cross_scope_isolation(self, cfg):
        """An owner of the OTHER scope has no write power on this scope.

        This pins the security-critical no-cross-scope-cascade property
        that the merge must preserve: an ``organization`` owner must not
        gain ``course_family`` privileges and vice versa.
        """
        _, HandlerCls, entity, scope_key, *_ = cfg
        other_scope = "course_family" if scope_key == "organization" else "organization"
        handler = HandlerCls(entity)
        p = _scoped(other_scope, "_owner", scope_id="S1")
        for action in ("update", "archive", "delete"):
            assert handler.can_perform_action(p, action, resource_id="S1") is False


# ===========================================================================
# build_query characterization
# ===========================================================================
class TestBuildQuery:
    @pytest.mark.parametrize("cfg", SCOPES, ids=_pid)
    @pytest.mark.parametrize("action", ["get", "list"])
    def test_admin_returns_plain_entity_query(self, cfg, action):
        _, HandlerCls, entity, *_ = cfg
        handler = HandlerCls(entity)
        db = _RecordingDB()
        q = handler.build_query(_admin(), action, db)
        assert isinstance(q, _FakeQ)
        # admin short-circuits to db.query(entity) with no Course cascade
        assert db.queried(entity)
        assert not db.queried(Course.organization_id)
        assert not db.queried(Course.course_family_id)

    @pytest.mark.parametrize("cfg", SCOPES, ids=_pid)
    @pytest.mark.parametrize("action", ["get", "list"])
    def test_read_cascades_through_correct_course_fk(self, cfg, action):
        _, HandlerCls, entity, scope_key, this_fk, other_fk = cfg
        handler = HandlerCls(entity)
        db = _RecordingDB()
        # non-admin, no general claim, no scoped role: read still builds the
        # course-cascade subquery, which is the differentiator we pin.
        handler.build_query(_no_access(), action, db)
        assert db.queried(this_fk), (
            f"{scope_key} read must cascade through its own Course FK"
        )
        assert not db.queried(other_fk), (
            f"{scope_key} read must NOT cascade through the other scope's FK"
        )
        assert db.queried(entity)

    @pytest.mark.parametrize("cfg", SCOPES, ids=_pid)
    @pytest.mark.parametrize("action", ["update", "archive", "delete"])
    def test_write_with_role_returns_entity_query_no_cascade(self, cfg, action):
        _, HandlerCls, entity, scope_key, *_ = cfg
        handler = HandlerCls(entity)
        db = _RecordingDB()
        p = _scoped(scope_key, "_owner", scope_id="S1")
        q = handler.build_query(p, action, db)
        assert isinstance(q, _FakeQ)
        # write path filters entity.id in the held scope ids; no Course cascade
        assert db.queried(entity)
        assert not db.queried(Course.organization_id)
        assert not db.queried(Course.course_family_id)

    @pytest.mark.parametrize("cfg", SCOPES, ids=_pid)
    @pytest.mark.parametrize("action", ["update", "archive", "delete"])
    def test_write_without_role_returns_empty_sentinel(self, cfg, action):
        _, HandlerCls, entity, *_ = cfg
        handler = HandlerCls(entity)
        db = _RecordingDB()
        # no scoped role → empty-id filter sentinel, NOT a raise.
        q = handler.build_query(_no_access(), action, db)
        assert isinstance(q, _FakeQ)
        assert db.queried(entity)

    @pytest.mark.parametrize("cfg", SCOPES, ids=_pid)
    def test_general_permission_returns_plain_entity_query(self, cfg):
        _, HandlerCls, entity, *_ = cfg
        handler = HandlerCls(entity)
        db = _RecordingDB()
        q = handler.build_query(_general(handler), "delete", db)
        assert isinstance(q, _FakeQ)
        assert db.queried(entity)
        assert not db.queried(Course.organization_id)
        assert not db.queried(Course.course_family_id)

    @pytest.mark.parametrize("cfg", SCOPES, ids=_pid)
    def test_unsupported_action_raises_forbidden(self, cfg):
        _, HandlerCls, entity, *_ = cfg
        handler = HandlerCls(entity)
        db = _RecordingDB()
        # create is neither read nor in the write role map → Forbidden.
        with pytest.raises(ForbiddenException):
            handler.build_query(_no_access(), "create", db)
