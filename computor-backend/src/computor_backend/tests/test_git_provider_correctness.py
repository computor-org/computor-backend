"""Correctness fixes on the git-provider paths.

Pure unit tests with fakes — no DB, no live git server.
"""

from types import SimpleNamespace

import pytest

from computor_backend.git_provider.gitlab import GitLabProviderClient
from computor_types.accounts import AccountGet


class TestAccountSecretsAreNotSerialized:
    """A student's Forgejo clone tokens live on their OIDC account under
    ``properties``. They are encrypted and only the owner can read their own
    accounts, but credential material should not ride along in a response whose
    job is describing an identity."""

    def account(self, properties):
        return AccountGet(
            id="a1",
            provider="keycloak",
            type="oidc",
            provider_account_id="sub-123",
            user_id="u1",
            properties=properties,
        )

    def test_clone_tokens_are_dropped(self):
        account = self.account({
            "email": "student@example.org",
            "forgejo_clone_tokens": {"srv-1": "gAAAAA-ciphertext"},
        })
        assert account.properties == {"email": "student@example.org"}
        assert "gAAAAA-ciphertext" not in account.model_dump_json()

    def test_everything_else_survives(self):
        properties = {"email": "s@example.org", "username": "s", "groups": ["a"]}
        assert self.account(properties).properties == properties

    def test_tolerates_empty_and_missing_properties(self):
        assert self.account(None).properties is None
        assert self.account({}).properties == {}


class TestNamespaceIdComparison:
    """``_find_project_in_namespace`` compared an int from the GitLab API with
    whatever the caller passed. Ids read back out of a JSONB properties blob can
    be either type, and an untyped ``==`` silently never matches across the two —
    so an existing project looked absent and got created (or forked) again."""

    def client_with(self, projects):
        client = GitLabProviderClient("https://gitlab.example", "token", None)
        client._gl = lambda: SimpleNamespace(
            projects=SimpleNamespace(
                list=lambda search=None, all=False: projects,
                get=lambda pid: next(p for p in projects if p.id == pid),
            )
        )
        return client

    def project(self, namespace_id):
        return SimpleNamespace(id=7, path="template", namespace={"id": namespace_id})

    def test_matches_an_int_namespace_against_a_string_id(self):
        client = self.client_with([self.project(5678)])
        assert client._find_project_in_namespace(client._gl(), "5678", "template") is not None

    def test_matches_a_string_namespace_against_an_int_id(self):
        client = self.client_with([self.project("5678")])
        assert client._find_project_in_namespace(client._gl(), 5678, "template") is not None

    def test_still_rejects_a_genuinely_different_namespace(self):
        client = self.client_with([self.project(5678)])
        assert client._find_project_in_namespace(client._gl(), 9999, "template") is None


class TestGitLabClientHasATimeout:
    def test_client_is_constructed_with_a_timeout(self):
        """These calls run inside request handlers and Temporal activities; an
        unbounded client lets a hung GitLab hold them open indefinitely."""
        from computor_backend.git_provider.gitlab import make_gitlab_client

        client = make_gitlab_client("https://gitlab.example", "token")
        assert client.timeout == 30


class TestRemoveCollaborator:
    """A member removed from a course used to keep write access to their
    repository on the git server forever."""

    def client_with_response(self, status_code):
        from computor_backend.git_provider.forgejo import ForgejoProviderClient

        calls = []

        class _Response:
            def __init__(self, code):
                self.status_code = code

        class _Client:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *args):
                return False

            def delete(self_inner, url):
                calls.append(url)
                return _Response(status_code)

        client = ForgejoProviderClient.__new__(ForgejoProviderClient)
        client._client = lambda: _Client()
        return client, calls

    def test_revokes_the_grant(self):
        client, calls = self.client_with_response(204)
        assert client.remove_collaborator("course-org", "jane", "jane") is True
        assert calls == ["/api/v1/repos/course-org/jane/collaborators/jane"]

    def test_treats_already_gone_as_success(self):
        """A grant (or repo) that is already absent is the state we wanted."""
        client, _ = self.client_with_response(404)
        assert client.remove_collaborator("course-org", "jane", "jane") is True

    def test_reports_a_real_failure(self):
        client, _ = self.client_with_response(500)
        assert client.remove_collaborator("course-org", "jane", "jane") is False


class TestEndpointsRunOffTheEventLoop:
    """The git provisioning endpoints issue blocking HTTP — a Forgejo
    ``POST /repos/migrate`` clones the template server-side, and a GitLab fork
    poll can run 30 seconds. Awaited inline on the event loop they stall every
    other request the worker is serving."""

    def source(self):
        import pathlib

        import computor_backend.api.user as module

        return pathlib.Path(module.__spec__.origin).read_text()

    @pytest.mark.parametrize(
        "call",
        [
            "provision_student_repository",
            "register_gitlab_managed_access",
            "get_template_access",
        ],
    )
    def test_blocking_business_logic_is_offloaded(self, call):
        import re

        # `run_in_threadpool(<name>` allowing for the argument being wrapped
        # onto the following line.
        pattern = re.compile(rf"run_in_threadpool\(\s*{re.escape(call)}\b")
        assert pattern.search(self.source()), (
            f"{call} is called from an async endpoint and blocks on HTTP; "
            "it must be dispatched via run_in_threadpool"
        )
