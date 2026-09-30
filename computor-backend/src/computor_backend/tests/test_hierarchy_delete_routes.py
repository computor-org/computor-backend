"""Route-level rules for deleting organizations, course families and courses.

Everything below runs against the FastAPI app with the database and the
cascade/git side effects monkeypatched, so it pins the *decisions* the three
``DELETE`` endpoints make — who may call them, what blocks them, what a dry
run reports — not the SQL.

Rules (release 2026.10):
- only a scope ``_owner`` or an admin may delete; ``_organization_manager``
  is deliberately NOT enough;
- an organization / course family must have no children (409);
- a course with submissions from students can never be deleted by its owner
  (409), and an admin only once it is archived (409 until then);
- a dry run is permission-checked like the real call and reports the block
  as ``blocked_reason`` instead of failing.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from computor_backend.permissions.principal import Principal, build_claims
from computor_types.cascade_deletion import CascadeDeleteResult, EntityDeleteCount


COURSE_ID = str(uuid4())
FAMILY_ID = str(uuid4())
ORG_ID = str(uuid4())


def _principal(*claims, is_admin=False, roles=None):
    return Principal(
        user_id="u-1",
        is_admin=is_admin,
        roles=list(roles or ["user"]),
        claims=build_claims([("permissions", c) for c in claims]),
    )


def _admin():
    return Principal(user_id="admin", is_admin=True, roles=["_admin"])


def _course_owner():
    return _principal(f"course:_owner:{COURSE_ID}")


def _course_maintainer():
    return _principal(f"course:_maintainer:{COURSE_ID}")


def _org_manager():
    return _principal(roles=["_organization_manager"])


# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------

@pytest.fixture
def course_api(monkeypatch, mock_db):
    """Patch every side effect of ``api.courses.delete_course_endpoint``.

    Returns a configurator: ``course_api(student_submissions=, archived=)``
    sets up the course row and the counts, and hands back a recorder of what
    the endpoint did.
    """
    from computor_backend.api import courses as api

    rec = SimpleNamespace(cascade_calls=[], teardown_calls=[], invalidated=[], published=[])

    def _configure(student_submissions=0, archived=False, git_repos=None, cascade_errors=None):
        course = SimpleNamespace(
            id=COURSE_ID,
            archived_at=datetime.now(timezone.utc) if archived else None,
        )
        mock_db.query.return_value.filter.return_value.first.return_value = course
        counts = EntityDeleteCount(student_submissions=student_submissions, submission_artifacts=student_submissions)
        monkeypatch.setattr(api, "count_course_entities", lambda db, cid: counts)

        plan = SimpleNamespace(
            repos=[(f"forgejo:{r}", r) for r in (git_repos or [])],
            repo_labels=[f"forgejo:{r}" for r in (git_repos or [])],
            student_repositories_kept=7,
        )
        monkeypatch.setattr(api, "plan_course_git_teardown", lambda cid, db: plan)

        async def fake_cascade(db, course_id, storage=None, dry_run=False, counts=None):
            rec.cascade_calls.append(dry_run)
            return CascadeDeleteResult(
                dry_run=dry_run, entity_type="course", entity_id=course_id,
                deleted_counts=counts, errors=list(cascade_errors or []),
            )

        monkeypatch.setattr(api, "delete_course_cascade", fake_cascade)

        def fake_teardown(p, db):
            rec.teardown_calls.append(p)
            return list(p.repo_labels), []

        monkeypatch.setattr(api, "execute_course_git_teardown", fake_teardown)
        monkeypatch.setattr(api, "get_storage_service", lambda: object())
        monkeypatch.setattr(api, "invalidate_user_membership_caches", lambda uid: rec.invalidated.append(uid))
        monkeypatch.setattr(api, "publish_course_updated", lambda cid, change: rec.published.append(change))

        async def fake_principal(request, what=""):
            rec.invalidated.append("principal")

        monkeypatch.setattr(api, "invalidate_request_principal", fake_principal)
        monkeypatch.setattr(api.course_router, "_invalidate_caches_for", lambda entity: rec.invalidated.append(f"tags:{entity.id}"))
        return rec

    return _configure


def _delete_course(client, dry_run=False):
    return client.delete(f"/courses/{COURSE_ID}", params={"dry_run": str(dry_run).lower()})


class TestCourseDeletePermissions:
    def test_maintainer_is_forbidden(self, test_client_factory, course_api):
        course_api()
        client = test_client_factory(_course_maintainer())
        try:
            assert _delete_course(client).status_code == 403
            # The preview is not for people who could not delete either.
            assert _delete_course(client, dry_run=True).status_code == 403
        finally:
            client.cleanup()

    def test_organization_manager_is_forbidden(self, test_client_factory, course_api):
        course_api()
        client = test_client_factory(_org_manager())
        try:
            assert _delete_course(client).status_code == 403
        finally:
            client.cleanup()

    def test_owner_of_another_course_is_forbidden(self, test_client_factory, course_api):
        course_api()
        client = test_client_factory(_principal(f"course:_owner:{uuid4()}"))
        try:
            assert _delete_course(client).status_code == 403
        finally:
            client.cleanup()


class TestCourseDeleteRules:
    def test_owner_deletes_a_course_without_student_submissions(self, test_client_factory, course_api):
        rec = course_api(student_submissions=0, git_repos=["o/template", "o/reference"])
        client = test_client_factory(_course_owner())
        try:
            r = _delete_course(client)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["git_repositories"] == ["forgejo:o/template", "forgejo:o/reference"]
            assert body["student_repositories_kept"] == 7
            assert body["blocked_reason"] is None
            assert rec.cascade_calls == [False]
            assert len(rec.teardown_calls) == 1
            assert "principal" in rec.invalidated and f"tags:{COURSE_ID}" in rec.invalidated
            assert rec.published == ["deleted"]
        finally:
            client.cleanup()

    def test_owner_is_blocked_by_student_submissions(self, test_client_factory, course_api):
        rec = course_api(student_submissions=3)
        client = test_client_factory(_course_owner())
        try:
            r = _delete_course(client)
            assert r.status_code == 409, r.text
            assert "administrator" in r.text
            assert rec.cascade_calls == []
        finally:
            client.cleanup()

    def test_archiving_does_not_unlock_the_owner(self, test_client_factory, course_api):
        course_api(student_submissions=3, archived=True)
        client = test_client_factory(_course_owner())
        try:
            r = _delete_course(client)
            assert r.status_code == 409
            assert "administrator" in r.text
        finally:
            client.cleanup()

    def test_admin_must_archive_first(self, test_client_factory, course_api):
        rec = course_api(student_submissions=3, archived=False)
        client = test_client_factory(_admin())
        try:
            r = _delete_course(client)
            assert r.status_code == 409
            assert "Archive the course first" in r.text
            assert rec.cascade_calls == []
        finally:
            client.cleanup()

    def test_admin_deletes_an_archived_course(self, test_client_factory, course_api):
        rec = course_api(student_submissions=3, archived=True, git_repos=["o/template"])
        client = test_client_factory(_admin())
        try:
            r = _delete_course(client)
            assert r.status_code == 200, r.text
            assert r.json()["git_repositories"] == ["forgejo:o/template"]
            assert rec.cascade_calls == [False]
        finally:
            client.cleanup()

    def test_dry_run_reports_the_block_instead_of_failing(self, test_client_factory, course_api):
        rec = course_api(student_submissions=3, git_repos=["o/template", "o/reference"])
        client = test_client_factory(_course_owner())
        try:
            r = _delete_course(client, dry_run=True)
            assert r.status_code == 200, r.text
            body = r.json()
            assert "administrator" in body["blocked_reason"]
            assert body["dry_run"] is True
            assert body["deleted_counts"]["student_submissions"] == 3
            # The preview still says what a delete WOULD remove and keep.
            assert body["git_repositories"] == ["forgejo:o/template", "forgejo:o/reference"]
            assert body["student_repositories_kept"] == 7
            assert rec.cascade_calls == [True]
            assert rec.teardown_calls == []
            assert rec.published == []
        finally:
            client.cleanup()

    def test_git_teardown_is_skipped_when_the_cascade_failed(self, test_client_factory, course_api):
        rec = course_api(git_repos=["o/template"], cascade_errors=["Database error: boom"])
        client = test_client_factory(_course_owner())
        try:
            r = _delete_course(client)
            assert r.status_code == 200
            body = r.json()
            assert body["errors"] == ["Database error: boom"]
            assert body["git_repositories"] == []
            assert rec.teardown_calls == []
            assert rec.published == []
        finally:
            client.cleanup()


# ---------------------------------------------------------------------------
# Organization / course family
# ---------------------------------------------------------------------------

@pytest.fixture
def scope_api(monkeypatch, mock_db):
    from computor_backend.api import course_families as fam_api
    from computor_backend.api import organizations as org_api

    rec = SimpleNamespace(cascade_calls=[], invalidated=[])

    def _configure(children=0):
        row = SimpleNamespace(id=ORG_ID)
        mock_db.query.return_value.filter.return_value.first.return_value = row
        mock_db.query.return_value.filter.return_value.count.return_value = children

        def make_cascade(entity_type, key):
            async def fake(db, storage=None, dry_run=False, **kw):
                rec.cascade_calls.append((entity_type, dry_run))
                return CascadeDeleteResult(
                    dry_run=dry_run, entity_type=entity_type, entity_id=kw[key],
                    deleted_counts=EntityDeleteCount(),
                )
            return fake

        monkeypatch.setattr(org_api, "delete_organization_cascade", make_cascade("organization", "organization_id"))
        monkeypatch.setattr(fam_api, "delete_course_family_cascade", make_cascade("course_family", "course_family_id"))
        for mod in (org_api, fam_api):
            monkeypatch.setattr(mod, "get_storage_service", lambda: object())

            async def fake_principal(request, what=""):
                rec.invalidated.append("principal")

            monkeypatch.setattr(mod, "invalidate_request_principal", fake_principal)
        monkeypatch.setattr(org_api.organization_router, "_invalidate_caches_for", lambda e: rec.invalidated.append("org-tags"))
        monkeypatch.setattr(fam_api.course_family_router, "_invalidate_caches_for", lambda e: rec.invalidated.append("family-tags"))
        return rec

    return _configure


@pytest.mark.parametrize(
    "path,claim_scope,scope_id",
    [
        (f"/organizations/{ORG_ID}", "organization", ORG_ID),
        (f"/course-families/{FAMILY_ID}", "course_family", FAMILY_ID),
    ],
    ids=["organization", "course_family"],
)
class TestScopeDelete:
    def test_organization_manager_is_forbidden(self, test_client_factory, scope_api, path, claim_scope, scope_id):
        scope_api()
        client = test_client_factory(_org_manager())
        try:
            assert client.delete(path).status_code == 403
            assert client.delete(path, params={"dry_run": "true"}).status_code == 403
        finally:
            client.cleanup()

    def test_scope_manager_is_forbidden(self, test_client_factory, scope_api, path, claim_scope, scope_id):
        scope_api()
        client = test_client_factory(_principal(f"{claim_scope}:_manager:{scope_id}"))
        try:
            assert client.delete(path).status_code == 403
        finally:
            client.cleanup()

    def test_owner_is_blocked_while_children_exist(self, test_client_factory, scope_api, path, claim_scope, scope_id):
        rec = scope_api(children=2)
        client = test_client_factory(_principal(f"{claim_scope}:_owner:{scope_id}"))
        try:
            r = client.delete(path)
            assert r.status_code == 409, r.text
            assert "Delete them first" in r.text
            assert rec.cascade_calls == []
            preview = client.delete(path, params={"dry_run": "true"})
            assert preview.status_code == 200
            assert "Delete them first" in preview.json()["blocked_reason"]
        finally:
            client.cleanup()

    def test_owner_deletes_an_empty_scope(self, test_client_factory, scope_api, path, claim_scope, scope_id):
        rec = scope_api(children=0)
        client = test_client_factory(_principal(f"{claim_scope}:_owner:{scope_id}"))
        try:
            r = client.delete(path)
            assert r.status_code == 200, r.text
            assert r.json()["blocked_reason"] is None
            assert rec.cascade_calls == [(claim_scope, False)]
            assert "principal" in rec.invalidated
        finally:
            client.cleanup()

    def test_admin_deletes_an_empty_scope(self, test_client_factory, scope_api, path, claim_scope, scope_id):
        rec = scope_api(children=0)
        client = test_client_factory(_admin())
        try:
            assert client.delete(path).status_code == 200
            assert rec.cascade_calls == [(claim_scope, False)]
        finally:
            client.cleanup()
