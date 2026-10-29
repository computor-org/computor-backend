"""Keycloak `locale` attribute sync from the profile language (issues#555).

Keycloak picks the language of its own pages (OTP, update-password, info)
from the `locale` user attribute once the user is identified; the profile
save must mirror it, and must never fail when Keycloak is unreachable.
"""

import asyncio

import computor_backend.auth.keycloak_admin as kc_mod


class _Response:
    def __init__(self, body=None, status_code=204):
        self._body = body
        self.status_code = status_code

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _wire(monkeypatch, user, fail_get=False, fail_put=False):
    puts = []

    class _Client:
        def __init__(self, *args, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, params=None, headers=None):
            if fail_get:
                raise ConnectionError("keycloak down")
            return _Response(dict(user), 200)

        async def put(self, url, json=None, headers=None):
            if fail_put:
                return _Response({}, 500)
            puts.append(json)
            return _Response()

    async def _token(self):
        return "tok"

    monkeypatch.setattr(kc_mod.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(kc_mod.KeycloakAdminClient, "_get_admin_token", _token)
    return puts


def _user(**over):
    return {"id": "kc-1", "username": "someone", "attributes": {}, **over}


def test_locale_is_set(monkeypatch):
    puts = _wire(monkeypatch, _user())
    asyncio.run(kc_mod.KeycloakAdminClient().set_user_locale("kc-1", "de"))
    assert len(puts) == 1
    assert puts[0]["attributes"]["locale"] == ["de"]
    assert puts[0]["username"] == "someone"  # full representation is preserved


def test_locale_is_replaced(monkeypatch):
    puts = _wire(monkeypatch, _user(attributes={"locale": ["en"], "other": ["x"]}))
    asyncio.run(kc_mod.KeycloakAdminClient().set_user_locale("kc-1", "de"))
    assert puts[0]["attributes"] == {"locale": ["de"], "other": ["x"]}


def test_locale_is_removed_for_automatic(monkeypatch):
    puts = _wire(monkeypatch, _user(attributes={"locale": ["en"], "other": ["x"]}))
    asyncio.run(kc_mod.KeycloakAdminClient().set_user_locale("kc-1", None))
    assert puts[0]["attributes"] == {"other": ["x"]}


def test_matching_locale_writes_nothing(monkeypatch):
    puts = _wire(monkeypatch, _user(attributes={"locale": ["de"]}))
    asyncio.run(kc_mod.KeycloakAdminClient().set_user_locale("kc-1", "de"))
    assert puts == []
    puts = _wire(monkeypatch, _user())
    asyncio.run(kc_mod.KeycloakAdminClient().set_user_locale("kc-1", None))
    assert puts == []


def test_unreachable_keycloak_never_raises(monkeypatch):
    _wire(monkeypatch, _user(), fail_get=True)
    asyncio.run(kc_mod.KeycloakAdminClient().set_user_locale("kc-1", "de"))
    _wire(monkeypatch, _user(), fail_put=True)
    asyncio.run(kc_mod.KeycloakAdminClient().set_user_locale("kc-1", "de"))


class _Query:
    def __init__(self, row):
        self._row = row

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._row


class _FakeDB:
    def __init__(self, row):
        self._row = row

    def query(self, *args, **kwargs):
        return _Query(self._row)


def test_profile_save_syncs_the_locale(monkeypatch):
    import computor_backend.business_logic.profiles as profiles

    calls = []

    class FakeKC:
        async def set_user_locale(self, kc_user_id, locale):
            calls.append((kc_user_id, locale))

    monkeypatch.setattr(profiles, "KeycloakAdminClient", lambda: FakeKC())
    asyncio.run(profiles.sync_keycloak_locale(_FakeDB(("kc-1",)), "u1", "de"))
    asyncio.run(profiles.sync_keycloak_locale(_FakeDB(None), "u2", "de"))
    assert calls == [("kc-1", "de")]  # no Keycloak account: nothing synced


def test_profile_save_survives_a_failing_sync(monkeypatch):
    import computor_backend.business_logic.profiles as profiles

    class BrokenKC:
        async def set_user_locale(self, kc_user_id, locale):
            raise ConnectionError("keycloak down")

    monkeypatch.setattr(profiles, "KeycloakAdminClient", lambda: BrokenKC())
    asyncio.run(profiles.sync_keycloak_locale(_FakeDB(("kc-1",)), "u1", "de"))


def test_patch_endpoint_syncs_only_when_language_is_saved(monkeypatch):
    import computor_backend.api.profiles as api
    from computor_backend.model.auth import Profile
    from computor_backend.permissions.principal import Principal
    from computor_types.profiles import ProfileUpdate

    calls = []

    async def fake_sync(db, user_id, language_code):
        calls.append((user_id, language_code))

    profile = Profile(id="p1", user_id="u1", language_code="de", nickname="ada")
    monkeypatch.setattr(api, "update_profile", lambda *a, **k: profile)
    monkeypatch.setattr(api, "sync_keycloak_locale", fake_sync)
    principal = Principal(user_id="u1", roles=["user"])

    asyncio.run(api.update_profile_endpoint(principal, "p1", ProfileUpdate(language_code="de"), db=None))
    assert calls == [("u1", "de")]

    calls.clear()
    asyncio.run(api.update_profile_endpoint(principal, "p1", ProfileUpdate(nickname="ada2"), db=None))
    assert calls == []  # a save without a language change does not touch Keycloak
