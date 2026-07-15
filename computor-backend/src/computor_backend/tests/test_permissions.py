"""Consolidated permission tests (P6.2).

Merges the former ``test_permissions_{simple,practical,mocked,comprehensive,
comprehensive_fixed}.py`` into one hermetic suite. Those five overlapped heavily
and had rotted (they imported the moved ``computor_backend.api.crud`` module and
a stale ``MockPrincipal`` that lacked methods the real code calls), so they are
replaced here by a single correct file built against the *real* ``Principal`` and
the *real* FastAPI app with a mocked DB.

Three sections:

* ``TestPermissionCore`` — unit tests of ``Principal`` / ``Claims`` / the
  ``check_*`` / ``can_perform_*`` helpers. These carry the real authorization
  coverage and are preserved verbatim from the old ``_simple.py``.
* ``TestPermissionEndpoints`` — a persona x endpoint matrix driven against the
  real app with ``mock_db``. Because the mock DB returns empty result sets and
  request-body validation runs *before* authorization, list reads are
  scope-filtered to 200 and creates hit validation (400/422) for every persona;
  the mock cannot express fine-grained row-level authz. So this layer is a
  *wiring/intent smoke guard*: endpoints never 500, denied personas never create
  (never 201), and an allowed persona is never outright forbidden (never 403).
  The fine-grained allow/deny logic is asserted in ``TestPermissionCore``.
* ``TestPermissionBehavior`` — role-hierarchy / admin-full-access / lifecycle
  flows ported onto the real ``Principal``.

All hermetic (``mock_db`` only) → marked ``unit``.
"""

import pytest
from fastapi.testclient import TestClient

from computor_backend.server import app
from computor_backend.permissions.auth import get_current_principal
from computor_backend.database import get_db
from computor_backend.permissions.principal import Principal, Claims, build_claims
from computor_backend.permissions.core import (
    check_permissions,
    check_admin,
    can_perform_on_resource,
    can_perform_with_parents,
)
from computor_backend.exceptions import ForbiddenException

pytestmark = pytest.mark.unit

COURSE_ID = "course-123"


# ---------------------------------------------------------------------------
# Section 1 — core helper unit tests (preserved verbatim from _simple.py).
# These are the real authorization coverage: they exercise the Principal /
# claims / check_* helpers directly, independent of any endpoint plumbing.
# ---------------------------------------------------------------------------

class TestPermissionCore:
    """Unit tests for the Principal, claims and permission helpers."""

    def test_principal_creation(self):
        """Creating principals with different roles."""
        admin = Principal(user_id='admin-123', is_admin=True, roles=['system_admin'])
        assert admin.user_id == 'admin-123'
        assert admin.is_admin is True
        assert admin.permitted('anything', 'anything')  # Admin can do anything

        student = Principal(user_id='student-123', is_admin=False, roles=['student'])
        assert student.user_id == 'student-123'
        assert student.is_admin is False
        assert not student.permitted('course', 'create')  # Student can't create courses

    def test_course_roles(self):
        """Course role claims land under the dependent scope."""
        principal = Principal(user_id='lecturer-123', is_admin=False, roles=['lecturer'])
        claims = Claims()
        claims.dependent['course-456'] = {'_lecturer'}
        principal.claims = claims
        assert '_lecturer' in principal.claims.dependent.get('course-456', set())

    def test_check_admin_function(self):
        """``check_admin`` is True for admins, False otherwise."""
        admin = Principal(user_id='admin-1', is_admin=True, roles=['admin'])
        assert check_admin(admin) is True

        student = Principal(user_id='student-1', is_admin=False, roles=['student'])
        assert check_admin(student) is False

    def test_permission_caching(self):
        """Repeated permission checks are stable (and cached)."""
        principal = Principal(user_id='test-user', is_admin=True)
        result1 = principal.permitted('resource', 'action')
        result2 = principal.permitted('resource', 'action')
        assert result1 is True
        assert result2 is True
        assert result1 == result2

    def test_general_and_dependent_permissions(self):
        """General and dependent claims are respected independently."""
        claim_values = [
            ("permissions", "organization:list"),
            ("permissions", "course_content:update:cc-1"),
        ]
        principal = Principal(user_id='u1', roles=['user'], claims=build_claims(claim_values))
        assert principal.permitted('organization', 'list') is True
        assert principal.permitted('course_content', 'update', 'cc-1') is True
        assert principal.permitted('course_content', 'update', 'cc-2') is False

    def test_course_role_permission_check(self):
        """Course-scoped role claims gate by course id and role rank."""
        course_id = 'course-abc'
        principal = Principal(
            user_id='u2', roles=['tutor'],
            claims=build_claims([("permissions", f"course:_tutor:{course_id}")]),
        )
        assert principal.permitted('course', 'get', course_id, course_role='_student') is True
        assert principal.permitted('course', 'get', 'course-other', course_role='_student') is False

    def test_registry_no_handler_fallback(self, mock_db):
        """With no registered handler, non-admins are forbidden, admins get a query."""
        class Dummy:
            __tablename__ = 'dummy'

        admin = Principal(user_id='a1', is_admin=True, roles=['system_admin'])
        non_admin = Principal(user_id='u3', roles=['user'])

        q = check_permissions(admin, Dummy, 'list', mock_db)
        assert hasattr(q, 'filter')

        with pytest.raises(ForbiddenException):
            check_permissions(non_admin, Dummy, 'list', mock_db)

    def test_general_helpers_for_resource_and_parents(self):
        """``can_perform_on_resource`` / ``can_perform_with_parents`` helpers."""
        p1 = Principal(user_id='u10', roles=['user'], claims=build_claims([
            ('permissions', 'widgets:create')
        ]))
        assert can_perform_on_resource(p1, 'widgets', 'create') is True
        assert can_perform_on_resource(p1, 'widgets', 'delete') is False

        course_id = 'c-1'
        backend_id = 'eb-1'
        p2 = Principal(user_id='u20', roles=['lecturer'], claims=build_claims([
            ('permissions', f'course:_lecturer:{course_id}'),
            ('permissions', f'execution_backend:use:{backend_id}'),
        ]))
        context = {'course_id': course_id, 'execution_backend_id': backend_id}
        assert can_perform_with_parents(p2, 'create', context, min_course_role='_lecturer') is True

        p3 = Principal(user_id='u30', roles=['lecturer'], claims=build_claims([
            ('permissions', f'course:_lecturer:{course_id}')
        ]))
        assert can_perform_with_parents(p3, 'create', context, min_course_role='_lecturer') is False


# ---------------------------------------------------------------------------
# Section 2 — persona x endpoint smoke matrix against the real app + mock_db.
# ---------------------------------------------------------------------------

def _persona(user_id, *, is_admin=False, roles=None, course_role=None):
    kwargs = dict(user_id=user_id, is_admin=is_admin, roles=roles or [])
    if course_role:
        kwargs["claims"] = build_claims([("permissions", f"course:{course_role}:{COURSE_ID}")])
    return Principal(**kwargs)


@pytest.fixture
def personas():
    """The real ``Principal`` for each persona (admin + course-role cohort + anon)."""
    return {
        "admin": _persona("u-admin", is_admin=True, roles=["system_admin"]),
        "lecturer": _persona("u-lecturer", roles=["lecturer"], course_role="_lecturer"),
        "tutor": _persona("u-tutor", roles=["tutor"], course_role="_tutor"),
        "student": _persona("u-student", roles=["student"], course_role="_student"),
        "maintainer": _persona("u-maintainer", roles=["maintainer"], course_role="_maintainer"),
        "unauthorized": _persona("u-none", roles=[]),
    }


@pytest.fixture
def client_for(mock_db):
    """Build a ``TestClient`` whose auth + DB dependencies are overridden.

    ``raise_server_exceptions=False`` so a handler that reaches into the empty
    mock DB and raises (e.g. building a response DTO from ``None``) surfaces as a
    500 *response* rather than a re-raised exception — a 500 then simply means
    "authorization passed and the handler ran", which is the signal we want.
    """
    def _make(principal):
        app.dependency_overrides[get_current_principal] = lambda: principal
        app.dependency_overrides[get_db] = lambda: mock_db
        return TestClient(app, raise_server_exceptions=False)

    yield _make
    app.dependency_overrides.clear()


LIST_ENDPOINTS = ["/organizations", "/courses", "/course-contents", "/course-members", "/users"]
ALL_PERSONAS = ["admin", "lecturer", "tutor", "student", "maintainer", "unauthorized"]

# (persona, allowed?) intent for each create endpoint — "allowed" means the
# persona is authorized in principle (admin bypasses; course creates need
# org-manager/maintainer; content creates need lecturer-and-above).
ORG_CREATE = [("admin", True), ("lecturer", False), ("tutor", False),
              ("student", False), ("maintainer", False), ("unauthorized", False)]
COURSE_CREATE = [("admin", True), ("maintainer", True), ("lecturer", False),
                 ("tutor", False), ("student", False), ("unauthorized", False)]
CONTENT_CREATE = [("admin", True), ("lecturer", True), ("maintainer", True),
                  ("tutor", False), ("student", False), ("unauthorized", False)]
MEMBER_CREATE = [("admin", True), ("maintainer", True), ("lecturer", False),
                 ("tutor", False), ("student", False), ("unauthorized", False)]


class TestPermissionEndpoints:
    """Wiring/intent smoke matrix (see module docstring for why it is tolerant)."""

    @pytest.mark.parametrize("endpoint", LIST_ENDPOINTS)
    @pytest.mark.parametrize("persona", ALL_PERSONAS)
    def test_list_read_is_scope_filtered_never_500(self, personas, client_for, persona, endpoint):
        """Scope-filtered list reads never 500; the empty mock DB yields 200/404."""
        resp = client_for(personas[persona]).get(endpoint)
        assert resp.status_code in {200, 404}, \
            f"{persona} GET {endpoint} -> {resp.status_code}"

    @pytest.mark.parametrize("persona,allowed", ORG_CREATE)
    def test_create_organization_authz(self, personas, client_for, persona, allowed):
        resp = client_for(personas[persona]).post(
            "/organizations", json={"path": "test.org", "properties": {}})
        self._assert_create(resp, allowed, persona, "/organizations")

    @pytest.mark.parametrize("persona,allowed", COURSE_CREATE)
    def test_create_course_authz(self, personas, client_for, persona, allowed):
        resp = client_for(personas[persona]).post(
            "/courses", json={"path": "org.family.course", "properties": {"name": "C"}})
        self._assert_create(resp, allowed, persona, "/courses")

    @pytest.mark.parametrize("persona,allowed", CONTENT_CREATE)
    def test_create_course_content_authz(self, personas, client_for, persona, allowed):
        resp = client_for(personas[persona]).post(
            "/course-contents",
            json={"course_id": COURSE_ID, "title": "T", "content_type": "assignment", "properties": {}})
        self._assert_create(resp, allowed, persona, "/course-contents")

    @pytest.mark.parametrize("persona,allowed", MEMBER_CREATE)
    def test_create_course_member_authz(self, personas, client_for, persona, allowed):
        resp = client_for(personas[persona]).post(
            "/course-members",
            json={"course_id": COURSE_ID, "user_id": "new-user", "course_role_id": "_student"})
        self._assert_create(resp, allowed, persona, "/course-members")

    @staticmethod
    def _assert_create(resp, allowed, persona, endpoint):
        """The observable authz signal under mock_db. An allowed persona reaches
        the handler, so it is never outright forbidden (403) — it may 201, or
        400/422 on validation, or 500 building a response from the empty mock. A
        denied persona is stopped before the handler runs, so it never creates
        (201) and never reaches the handler body (500); it gets 400/401/403/404/422."""
        if allowed:
            assert resp.status_code != 403, \
                f"allowed {persona} POST {endpoint} was forbidden ({resp.status_code})"
        else:
            assert resp.status_code not in {201, 500}, \
                f"denied {persona} POST {endpoint} reached the handler ({resp.status_code})"


# ---------------------------------------------------------------------------
# Section 3 — behavior flows ported onto the real Principal.
# ---------------------------------------------------------------------------

class TestPermissionBehavior:
    """Role hierarchy, admin full access, and a course lifecycle flow."""

    def test_admin_has_full_access(self, personas, client_for):
        """Admin reads every top-level collection without 403/500."""
        client = client_for(personas["admin"])
        for endpoint in LIST_ENDPOINTS:
            status = client.get(endpoint).status_code
            assert status in {200, 404}, f"admin GET {endpoint} -> {status}"

    def test_role_hierarchy(self, personas, client_for):
        """A tutor cannot create content; a lecturer is not forbidden from it;
        a student can read the (scope-filtered) collections."""
        tutor_resp = client_for(personas["tutor"]).post(
            "/course-contents",
            json={"course_id": COURSE_ID, "title": "T", "content_type": "assignment"})
        assert tutor_resp.status_code != 201  # tutor cannot author content

        lecturer_resp = client_for(personas["lecturer"]).post(
            "/course-contents",
            json={"course_id": COURSE_ID, "title": "T", "content_type": "assignment", "properties": {}})
        assert lecturer_resp.status_code != 403  # lecturer is authorized in principle

        student_read = client_for(personas["student"]).get("/course-contents")
        assert student_read.status_code in {200, 404}

    def test_course_lifecycle_permissions(self, personas, client_for):
        """Admin may attempt the create chain (never forbidden); a student may
        not mutate content (never a 2xx)."""
        admin = client_for(personas["admin"])
        for endpoint, body in [
            ("/organizations", {"path": "test.university", "properties": {}}),
            ("/course-families", {"path": "test.university.cs", "properties": {"name": "CS"}}),
            ("/courses", {"path": "test.university.cs.101", "properties": {"name": "CS 101"}}),
        ]:
            status = admin.post(endpoint, json=body).status_code
            assert status != 403, f"admin POST {endpoint} was forbidden ({status})"

        student_modify = client_for(personas["student"]).patch(
            "/course-contents/content-123", json={"title": "Modified"})
        assert student_modify.status_code not in {200, 201, 204}  # student cannot modify content
