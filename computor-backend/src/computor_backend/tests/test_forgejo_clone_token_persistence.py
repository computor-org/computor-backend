"""Unit tests for the managed-Forgejo clone token's lifetime.

No DB and no live Forgejo: the account lookup, admin credentials and provider
client are faked, so these exercise only the decision logic in
``_provisioned_response`` and the token storage helpers.

Forgejo keeps ONE token per user and instance (rotation is keyed by token name)
and reveals its secret only at creation, so re-minting silently invalidates the
copy every already-cloned repo carries in its origin remote. Provisioning a
second course therefore used to break the first one's pushes with a bare 401
(computor-org/issues#332). The token is now minted once, remembered encrypted,
and re-minted only when the caller explicitly asks.
"""
from types import SimpleNamespace

import pytest
from keycove import generate_secret_key

from computor_backend.business_logic import course_git
from computor_backend.model.auth import Account
from computor_backend.model.git_server import GitServer

SERVER_ID = "srv-1"
FORGEJO = SimpleNamespace(id=SERVER_ID, type="forgejo", base_url="https://forge.example")


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class _FakeDb:
    """Answers ``query(GitServer)`` and ``query(Account)``; counts commits."""

    def __init__(self, server=FORGEJO, account=None):
        self.server = server
        self.account = account
        self.commits = 0

    def query(self, model):
        if model is GitServer:
            return _FakeQuery(self.server)
        if model is Account:
            return _FakeQuery(self.account)
        return _FakeQuery(None)

    def commit(self):
        self.commits += 1


class _FakeClient:
    """Mints a distinct token per call so rotation is observable."""

    def __init__(self, result="tok"):
        self.result = result
        self.calls = 0

    def mint_user_clone_token(self, username, admin_user, admin_password, name=None, scopes=None):
        self.calls += 1
        if self.result is None:
            return None
        return f"{self.result}-{self.calls}"


def _repo(mode="managed", git_server_id=SERVER_ID):
    return SimpleNamespace(mode=mode, git_server_id=git_server_id, course_member_id="cm-1")


@pytest.fixture
def wired(monkeypatch):
    """``_provisioned_response`` with its identity, credentials, provider client
    and repo serialization faked, plus an in-memory token store."""
    client = _FakeClient()
    store: dict = {}

    monkeypatch.setattr(course_git, "_resolve_oidc_handle", lambda user_id, db: "student42")
    monkeypatch.setattr(course_git, "_forgejo_admin_basic_auth_for", lambda server: ("admin", "pw"))
    monkeypatch.setattr(course_git, "get_provider_client_for_server", lambda server: client)
    monkeypatch.setattr(
        course_git,
        "_member_repo_to_get",
        lambda rec: SimpleNamespace(model_dump=lambda: {"id": "r-1", "course_member_id": "cm-1", "mode": rec.mode}),
    )
    monkeypatch.setattr(
        course_git, "_stored_clone_token", lambda user_id, server_id, db: store.get((user_id, str(server_id)))
    )
    monkeypatch.setattr(
        course_git,
        "_remember_clone_token",
        lambda user_id, server_id, token, db: store.__setitem__((user_id, str(server_id)), token),
    )
    return SimpleNamespace(client=client, store=store)


class TestProvisionedResponseTokenReuse:
    def test_mints_and_remembers_on_the_first_call(self, wired):
        out = course_git._provisioned_response(_repo(), "u-1", _FakeDb())

        assert out.clone_token == "tok-1"
        assert out.clone_username == "student42"
        assert wired.client.calls == 1
        assert wired.store[("u-1", SERVER_ID)] == "tok-1"

    def test_returns_the_same_token_on_later_calls(self, wired):
        first = course_git._provisioned_response(_repo(), "u-1", _FakeDb())
        second = course_git._provisioned_response(_repo(), "u-1", _FakeDb())

        # The whole point: provisioning another course must not invalidate the
        # credential already embedded in this student's existing clones.
        assert second.clone_token == first.clone_token == "tok-1"
        assert wired.client.calls == 1

    def test_rotate_mints_a_fresh_token_and_replaces_the_stored_one(self, wired):
        course_git._provisioned_response(_repo(), "u-1", _FakeDb())

        rotated = course_git._provisioned_response(_repo(), "u-1", _FakeDb(), rotate=True)

        assert rotated.clone_token == "tok-2"
        assert wired.client.calls == 2
        assert wired.store[("u-1", SERVER_ID)] == "tok-2"
        # And the rotated one is what later non-rotating calls hand out.
        assert course_git._provisioned_response(_repo(), "u-1", _FakeDb()).clone_token == "tok-2"

    def test_students_do_not_share_a_token(self, wired):
        a = course_git._provisioned_response(_repo(), "u-1", _FakeDb())
        b = course_git._provisioned_response(_repo(), "u-2", _FakeDb())

        assert a.clone_token != b.clone_token
        assert wired.client.calls == 2

    def test_a_failed_mint_is_not_remembered(self, wired, monkeypatch):
        # No Forgejo account yet (first OIDC login pending) — mint returns None
        # and the next call must try again rather than cache the failure.
        wired.client.result = None

        out = course_git._provisioned_response(_repo(), "u-1", _FakeDb())

        assert out.clone_token is None
        assert out.clone_username is None
        assert wired.store == {}

        wired.client.result = "tok"
        recovered = course_git._provisioned_response(_repo(), "u-1", _FakeDb())
        assert recovered.clone_token == "tok-2"

    def test_no_token_for_external_repos(self, wired):
        out = course_git._provisioned_response(_repo(mode="external"), "u-1", _FakeDb())

        assert out.clone_token is None
        assert wired.client.calls == 0

    def test_no_token_without_admin_credentials(self, wired, monkeypatch):
        # Not our configured managed Forgejo — never send admin creds there.
        monkeypatch.setattr(course_git, "_forgejo_admin_basic_auth_for", lambda server: None)

        out = course_git._provisioned_response(_repo(), "u-1", _FakeDb())

        assert out.clone_token is None
        assert wired.client.calls == 0


class TestCloneTokenStorage:
    """The real helpers: encrypted round-trip on the OIDC account row."""

    @pytest.fixture(autouse=True)
    def token_secret(self, monkeypatch):
        monkeypatch.setenv("TOKEN_SECRET", generate_secret_key())

    def test_round_trips_through_the_account_properties(self):
        account = SimpleNamespace(properties={"username": "student42"}, updated_by=None)
        db = _FakeDb(account=account)

        course_git._remember_clone_token("u-1", SERVER_ID, "secret-token", db)

        # Stored encrypted, never in the clear, and the handle survives.
        stored = account.properties[course_git._CLONE_TOKEN_PROP][SERVER_ID]
        assert stored != "secret-token"
        assert account.properties["username"] == "student42"
        assert account.updated_by == "u-1"
        assert db.commits == 1
        assert course_git._stored_clone_token("u-1", SERVER_ID, db) == "secret-token"

    def test_keeps_one_token_per_server(self):
        account = SimpleNamespace(properties={}, updated_by=None)
        db = _FakeDb(account=account)

        course_git._remember_clone_token("u-1", "srv-a", "token-a", db)
        course_git._remember_clone_token("u-1", "srv-b", "token-b", db)

        assert course_git._stored_clone_token("u-1", "srv-a", db) == "token-a"
        assert course_git._stored_clone_token("u-1", "srv-b", db) == "token-b"

    def test_missing_account_or_entry_reads_as_no_token(self):
        assert course_git._stored_clone_token("u-1", SERVER_ID, _FakeDb(account=None)) is None

        account = SimpleNamespace(properties={"username": "student42"}, updated_by=None)
        assert course_git._stored_clone_token("u-1", SERVER_ID, _FakeDb(account=account)) is None

    def test_storing_without_an_account_is_a_no_op(self):
        db = _FakeDb(account=None)
        course_git._remember_clone_token("u-1", SERVER_ID, "secret-token", db)
        assert db.commits == 0

    def test_undecryptable_ciphertext_reads_as_no_token(self):
        # e.g. TOKEN_SECRET was rotated — mint a fresh token instead of dying.
        account = SimpleNamespace(
            properties={course_git._CLONE_TOKEN_PROP: {SERVER_ID: "not-a-ciphertext"}}, updated_by=None
        )

        assert course_git._stored_clone_token("u-1", SERVER_ID, _FakeDb(account=account)) is None
