"""A self-registered Keycloak username must still give a Forgejo account.

Keycloak self-registration lets a learner choose any username, typically their
e-mail address. Forgejo refuses such a name with 422 "invalid username", so the
learner got no account, no clone token and no repository (computor-org/issues#433).
"""
from types import SimpleNamespace

import pytest

from computor_backend.business_logic import course_git
from computor_backend.utils import bootstrap_admin
from computor_backend.utils.git_username import forgejo_handle, is_forgejo_valid_username

FORGEJO = SimpleNamespace(id="srv-1", type="forgejo", base_url="http://computor-forgejo:3030")


@pytest.mark.parametrize("handle", ["mmusterm", "jane.doe", "a_b-c", "x1", "a" * 40])
def test_valid_handle_is_unchanged(handle):
    assert forgejo_handle(handle, "u-1") == handle


@pytest.mark.parametrize(
    "handle",
    [
        "qa-learner-1a2b@qa.computor.test",
        "Jane Doe",
        "müller",
        "trailing.",
        "a..b",
        "-lead",
        "admin",
        "@@@",
        "x" * 60 + "@example.com",
    ],
)
def test_invalid_handle_maps_to_a_valid_stable_name(handle):
    mapped = forgejo_handle(handle, "u-1")
    assert is_forgejo_valid_username(mapped), mapped
    assert forgejo_handle(handle, "u-1") == mapped


def test_mapping_keeps_the_readable_part_and_depends_on_the_user():
    mapped = forgejo_handle("qa-learner@qa.computor.test", "u-1")
    assert mapped.startswith("qa-learner-qa.computor.test-")
    assert forgejo_handle("qa-learner@qa.computor.test", "u-2") != mapped


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class _FakeDb:
    def query(self, model):
        return _FakeQuery(SimpleNamespace(id="u-1", email="qa-learner@qa.computor.test",
                                          given_name="Qa", family_name="Learner"))


class _StrictForgejo:
    """Creates an account only for a name Forgejo would accept."""

    def __init__(self):
        self.users = set()

    def ensure_user(self, username, email, full_name, admin_username, admin_password):
        if not is_forgejo_valid_username(username):
            return False
        self.users.add(username)
        return True


def test_email_username_gets_an_account(monkeypatch):
    client = _StrictForgejo()
    account = SimpleNamespace(properties={"username": "qa-learner@qa.computor.test"})
    monkeypatch.setattr(course_git, "_oidc_account", lambda user_id, db: account)
    monkeypatch.setattr(course_git, "_forgejo_admin_basic_auth_for", lambda server: ("admin", "pw"))
    monkeypatch.setattr(course_git, "get_provider_client_for_server", lambda server: client)
    monkeypatch.setattr(bootstrap_admin, "is_bootstrap_admin", lambda user: False)

    handle = course_git._ensure_forgejo_account("u-1", FORGEJO, _FakeDb())

    assert handle is not None
    assert client.users == {handle}
    # Every later grant and the clone token use the same name.
    assert course_git._resolve_oidc_handle("u-1", _FakeDb()) == handle
