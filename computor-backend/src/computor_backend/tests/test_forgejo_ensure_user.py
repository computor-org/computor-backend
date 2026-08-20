"""Unit tests for ``ForgejoProviderClient.ensure_user`` and the bootstrap-admin skip.

No live Forgejo: ``httpx.Client`` is monkeypatched, so these exercise only how
the provider reads Forgejo's answers.

Forgejo replies **422** to two very different outcomes of ``POST /admin/users``:
"user already exists" (the account is there — success) and "e-mail already in
use" (nothing was created). Treating both as success made a never-created
account look provisioned, and every later grant for that name failed forever —
422 on collaborators, 404 on team members and tokens — with nothing saying why.
"""
from types import SimpleNamespace

import pytest

from computor_backend.git_provider import forgejo as forgejo_mod
from computor_backend.git_provider.forgejo import ForgejoProviderClient
from computor_backend.utils import bootstrap_admin


class _Resp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload or "")

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class _FakeHttpClient:
    """Answers POST /admin/users with `create`, GET /users/{name} with `lookup`."""

    def __init__(self, create, lookup):
        self._create = create
        self._lookup = lookup
        self.gets = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, json=None):
        return self._create

    def get(self, url):
        self.gets.append(url)
        return self._lookup


@pytest.fixture
def client_factory(monkeypatch):
    """Return a callable wiring ``httpx.Client`` to one canned create/lookup pair."""

    def _wire(create, lookup=None):
        fake = _FakeHttpClient(create, lookup or _Resp(404))
        monkeypatch.setattr(forgejo_mod.httpx, "Client", lambda **kw: fake)
        return fake

    return _wire


def _ensure(provider=None):
    provider = provider or ForgejoProviderClient("https://forge.example", "tok")
    return provider.ensure_user("admin1", "admin@computor.local", "A B", "adm", "pw")


def test_created_account_is_success(client_factory):
    fake = client_factory(_Resp(201, {"login": "admin1"}))
    assert _ensure() is True
    # A successful create never needs the confirmation lookup.
    assert fake.gets == []


def test_existing_user_422_is_success(client_factory):
    """"user already exists" — the account IS there, which is what we wanted."""
    client_factory(
        _Resp(422, {"message": "user already exists [name: admin1]"}),
        lookup=_Resp(200, {"login": "admin1"}),
    )
    assert _ensure() is True


def test_email_conflict_422_is_failure(client_factory, caplog):
    """"e-mail already in use" creates nothing — the old code called this success."""
    client_factory(
        _Resp(422, {"message": "e-mail already in use [email: admin@computor.local]"}),
        lookup=_Resp(404),
    )
    with caplog.at_level("ERROR"):
        assert _ensure() is False
    assert "e-mail already in use" in caplog.text


def test_unparseable_body_still_fails_loudly(client_factory, caplog):
    client_factory(_Resp(500), lookup=_Resp(404))
    with caplog.at_level("ERROR"):
        assert _ensure() is False
    assert "admin1" in caplog.text


# --------------------------------------------------------------- bootstrap admin


def _user(email=None, properties=None):
    return SimpleNamespace(email=email, properties=properties)


@pytest.fixture
def bootstrap_email(monkeypatch):
    monkeypatch.setattr(
        bootstrap_admin, "bootstrap_admin_email", lambda: "admin@computor.local"
    )


def test_bootstrap_admin_recognised_by_email(bootstrap_email):
    assert bootstrap_admin.is_bootstrap_admin(_user("Admin@Computor.local")) is True
    assert bootstrap_admin.is_bootstrap_admin(_user("someone@else.org")) is False
    assert bootstrap_admin.is_bootstrap_admin(None) is False


def test_stamp_survives_a_changed_admin_email(monkeypatch):
    """The identity is the one the deployment was bootstrapped with, not whoever
    holds the address today."""
    monkeypatch.setattr(bootstrap_admin, "bootstrap_admin_email", lambda: "new@x.org")
    stamped = _user("old@x.org", {bootstrap_admin.BOOTSTRAP_ADMIN_PROP: True})
    assert bootstrap_admin.is_bootstrap_admin(stamped) is True


def test_stamp_is_written_once(bootstrap_email):
    user = _user("admin@computor.local", None)
    assert bootstrap_admin.stamp_bootstrap_admin(user) is True
    assert user.properties[bootstrap_admin.BOOTSTRAP_ADMIN_PROP] is True
    # Idempotent: nothing to commit on later logins.
    assert bootstrap_admin.stamp_bootstrap_admin(user) is False


def test_stamp_ignores_ordinary_users(bootstrap_email):
    user = _user("student@example.org", {"other": 1})
    assert bootstrap_admin.stamp_bootstrap_admin(user) is False
    assert user.properties == {"other": 1}
