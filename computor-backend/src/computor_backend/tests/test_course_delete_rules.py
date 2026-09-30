"""The rules behind ``DELETE /courses/{id}`` (release 2026.10).

Pure functions only — no database. The route-level wiring is covered by
``test_hierarchy_delete_routes.py``.

The policy: a course that holds submissions from students can never be
deleted by its owner; an administrator may, but only once the course has been
archived. Courses without student submissions delete directly.
"""
from types import SimpleNamespace

from computor_backend.business_logic.cascade_deletion import course_delete_block_reason
from computor_types.cascade_deletion import EntityDeleteCount


def _counts(student_submissions=0, **more):
    return EntityDeleteCount(student_submissions=student_submissions, **more)


def test_no_student_submissions_deletes_directly_for_everyone():
    counts = _counts(0, submission_artifacts=3, results=7, course_members=40)
    assert course_delete_block_reason(counts, archived=False, is_admin=False) is None
    assert course_delete_block_reason(counts, archived=False, is_admin=True) is None


def test_owner_is_blocked_by_student_submissions_even_when_archived():
    counts = _counts(1)
    for archived in (False, True):
        reason = course_delete_block_reason(counts, archived=archived, is_admin=False)
        assert reason is not None
        assert "administrator" in reason
        assert "1 submission " in reason


def test_admin_must_archive_first():
    counts = _counts(12)
    reason = course_delete_block_reason(counts, archived=False, is_admin=True)
    assert reason is not None
    assert "Archive the course first" in reason
    assert "12 submissions" in reason


def test_admin_may_delete_an_archived_course_with_student_submissions():
    assert course_delete_block_reason(_counts(12), archived=True, is_admin=True) is None


def test_staff_self_tests_do_not_count():
    """``student_submissions`` is what matters, not ``submission_artifacts``:
    a lecturer rehearsing the course through the student path must not lock
    the course against deletion."""
    counts = _counts(0, submission_artifacts=5)
    assert course_delete_block_reason(counts, archived=False, is_admin=False) is None


class TestTeardownPlan:
    """``plan_course_git_teardown`` resolves only the course's own repos."""

    class _Q:
        def __init__(self, rows):
            self._rows = rows

        def join(self, *a, **k):
            return self

        def filter(self, *a, **k):
            return self

        def count(self):
            return len(self._rows)

        def first(self):
            return self._rows[0] if self._rows else None

    class _Db:
        def __init__(self, repos=0, binding=None, server=None):
            from computor_backend.model.git_server import (
                CourseGitBinding,
                CourseMemberGitRepository,
                GitServer,
            )

            self._rows = {
                CourseMemberGitRepository: [object()] * repos,
                CourseGitBinding: [binding] if binding else [],
                GitServer: [server] if server else [],
            }

        def query(self, model):
            return TestTeardownPlan._Q(self._rows.get(model, []))

    def test_no_binding_means_no_teardown_but_counts_student_repos(self):
        from computor_backend.business_logic.course_git import plan_course_git_teardown

        plan = plan_course_git_teardown("c1", self._Db(repos=3))
        assert plan.repos == []
        assert plan.student_repositories_kept == 3

    def test_forgejo_course_org_layout(self):
        from computor_backend.business_logic.course_git import plan_course_git_teardown

        binding = SimpleNamespace(
            delivery="git",
            git_server_id="s1",
            template_repo="itpcp-2027/template",
            properties={"forgejo": {"layout": "course_org", "reference_repo": "itpcp-2027/reference"}},
            token=None,
        )
        server = SimpleNamespace(id="s1", type="forgejo", token=None)
        plan = plan_course_git_teardown("c1", self._Db(repos=25, binding=binding, server=server))
        assert plan.server_type == "forgejo"
        assert plan.repo_labels == ["forgejo:itpcp-2027/template", "forgejo:itpcp-2027/reference"]
        assert [ref for _, ref in plan.repos] == ["itpcp-2027/template", "itpcp-2027/reference"]
        # Never the students' repos, the org, the team or the tokens.
        assert plan.student_repositories_kept == 25

    def test_forgejo_legacy_layout_derives_the_reference_name(self):
        from computor_backend.business_logic.course_git import plan_course_git_teardown

        binding = SimpleNamespace(
            delivery="git", git_server_id="s1",
            template_repo="itpcp/matlab-2027-template", properties={}, token=None,
        )
        server = SimpleNamespace(id="s1", type="forgejo", token=None)
        plan = plan_course_git_teardown("c1", self._Db(binding=binding, server=server))
        assert [ref for _, ref in plan.repos] == [
            "itpcp/matlab-2027-template",
            "itpcp/matlab-2027--reference",
        ]

    def test_gitlab_uses_project_ids_and_shows_paths(self, monkeypatch):
        from computor_backend.business_logic import course_git

        binding = SimpleNamespace(
            delivery="git", git_server_id="s1", template_repo="grp/c/template", token="enc",
            properties={"gitlab": {
                "template_project_id": 11, "template_path": "grp/c/template",
                "reference_project_id": 12, "reference_path": "grp/c/reference",
                "students_group_id": 99,
            }},
        )
        server = SimpleNamespace(id="s1", type="gitlab", token=None)
        monkeypatch.setattr(
            "computor_backend.git_provider.token_resolution.resolve_binding_token",
            lambda b, s: "plain-token",
        )
        plan = course_git.plan_course_git_teardown("c1", self._Db(binding=binding, server=server))
        assert plan.token == "plain-token"
        assert plan.repo_labels == ["gitlab:grp/c/template", "gitlab:grp/c/reference"]
        assert [ref for _, ref in plan.repos] == ["11", "12"]

    def test_download_only_binding_has_nothing_to_tear_down(self):
        from computor_backend.business_logic.course_git import plan_course_git_teardown

        binding = SimpleNamespace(delivery="download", git_server_id="s1", template_repo=None, properties={}, token=None)
        plan = plan_course_git_teardown("c1", self._Db(binding=binding))
        assert plan.repos == []


class TestTeardownExecution:
    class _Db:
        def __init__(self, server):
            self._server = server

        def query(self, model):
            server = self._server

            class Q:
                def filter(self, *a, **k):
                    return self

                def first(self):
                    return server

            return Q()

    def test_forgejo_deletes_each_repo_and_reports_failures(self, monkeypatch):
        from computor_backend.business_logic import course_git
        from computor_backend.business_logic.course_git import CourseGitTeardownPlan

        calls = []

        class FakeClient:
            def delete_repo(self, owner, repo):
                calls.append((owner, repo))
                return repo != "reference"

        monkeypatch.setattr(course_git, "get_provider_client_for_server", lambda s: FakeClient())
        plan = CourseGitTeardownPlan(
            git_server_id="s1", server_type="forgejo",
            repos=[("forgejo:o/template", "o/template"), ("forgejo:o/reference", "o/reference")],
        )
        deleted, errors = course_git.execute_course_git_teardown(
            plan, self._Db(SimpleNamespace(id="s1", type="forgejo"))
        )
        assert calls == [("o", "template"), ("o", "reference")]
        assert deleted == ["forgejo:o/template"]
        assert errors == ["could not delete forgejo:o/reference"]

    def test_a_dead_server_is_an_error_not_an_exception(self, monkeypatch):
        from computor_backend.business_logic import course_git
        from computor_backend.business_logic.course_git import CourseGitTeardownPlan

        def boom(server):
            raise RuntimeError("connection refused")

        monkeypatch.setattr(course_git, "get_provider_client_for_server", boom)
        plan = CourseGitTeardownPlan(
            git_server_id="s1", server_type="forgejo", repos=[("forgejo:o/template", "o/template")]
        )
        deleted, errors = course_git.execute_course_git_teardown(
            plan, self._Db(SimpleNamespace(id="s1", type="forgejo"))
        )
        assert deleted == []
        assert errors and "connection refused" in errors[0]

    def test_empty_plan_is_a_noop(self):
        from computor_backend.business_logic.course_git import (
            CourseGitTeardownPlan,
            execute_course_git_teardown,
        )

        assert execute_course_git_teardown(CourseGitTeardownPlan(), self._Db(None)) == ([], [])
