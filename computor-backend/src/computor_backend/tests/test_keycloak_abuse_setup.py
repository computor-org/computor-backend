"""ops/keycloak/setup_abuse.py keeps the realm's other attributes (issues#478).

A realm PUT replaces Keycloak's whole attribute map, and the client and offline
session timeouts live in it. configure() sets the verification link lifespan
there, so it must send the attributes it read with the lifespan merged in, and
refuse to report success when any of them did not survive. The fake below
stores a realm PUT the way Keycloak does: an ``attributes`` key replaces the
stored map. The live counterpart is ops/keycloak/test_abuse_live.py.
"""

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "ops/keycloak"))
_spec = importlib.util.spec_from_file_location("setup_abuse_under_test", REPO / "ops/keycloak/setup_abuse.py")
setup_abuse = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(setup_abuse)

LIFESPAN_KEY = setup_abuse.VERIFY_EMAIL_LIFESPAN_ATTRIBUTE
MFA_RESET = "computor-reset-mfa"  # bound by ops/keycloak/setup_mfa.py
EXISTING = {
    "clientSessionIdleTimeout": "600",
    "clientSessionMaxLifespan": "1200",
    "clientOfflineSessionIdleTimeout": "600",
    "frontendUrl": "https://auth.example.invalid",
}


class FakeKeycloak:
    """The admin endpoints configure() calls, with a recorded realm PUT."""

    def __init__(self, drop_on_put=()):
        self.realm = {
            "registrationFlow": "registration",
            "resetCredentialsFlow": "reset credentials",
            "eventsListeners": ["jboss-logging"],
            "attributes": dict(EXISTING),
        }
        self.drop_on_put = drop_on_put
        self.realm_puts = []
        self.reset_execs = [{"id": "choose", "providerId": "reset-credentials-choose-user",
                             "requirement": "REQUIRED"}]
        self.flows = [{"alias": "registration"}, {"alias": "reset credentials"}]

    def request(self, method, path, body=None):
        if path == "":
            if method == "GET":
                return copy.deepcopy(self.realm)
            self.realm_puts.append(copy.deepcopy(body))
            for key, value in body.items():
                # Keycloak replaces the attribute map instead of merging it.
                self.realm[key] = copy.deepcopy(value)
            for key in self.drop_on_put:
                self.realm["attributes"].pop(key, None)
            return None
        if path.startswith("/components"):
            return []
        if path == "/users/profile":
            return {"attributes": [{"name": "email"}]} if method == "GET" else None
        if path.startswith("/users?"):
            return []
        if path == "/authentication/form-action-providers":
            return [{"id": "computor-registration-abuse"}]
        if path == "/authentication/authenticator-providers":
            return [{"id": "computor-reset-abuse"}]
        if path == "/authentication/flows":
            return list(self.flows)
        if path.endswith("/copy"):
            self.flows.append({"alias": body["newName"]})
            return None
        if path == f"/authentication/flows/{setup_abuse.REGISTRATION}/executions":
            return [{"id": "form", "authenticationFlow": True, "level": 0, "displayName": "form",
                     "providerId": "registration-page-form", "requirement": "REQUIRED"},
                    {"id": "reg-abuse", "providerId": "computor-registration-abuse",
                     "requirement": "REQUIRED", "authenticationConfig": "cfg-reg"}]
        if path in (f"/authentication/flows/{setup_abuse.RESET}/executions",
                    "/authentication/flows/computor-reset-mfa/executions"):
            if method == "PUT":
                return None
            return [{"id": "reset-abuse", "providerId": "computor-reset-abuse",
                     "requirement": "REQUIRED", "authenticationConfig": "cfg-reset"}] + self.reset_execs
        if path.startswith("/authentication/config/"):
            return {"config": {}} if method == "GET" else None
        raise AssertionError(f"unexpected {method} {path}")


@pytest.fixture
def fake(monkeypatch):
    kc = FakeKeycloak()
    monkeypatch.setattr(setup_abuse, "Client", lambda base, realm, token: kc)
    return kc


def _configure():
    return setup_abuse.configure("https://kc.example.invalid", "computor", "token", "s" * 32)


def test_realm_put_merges_the_lifespan_into_existing_attributes(fake):
    _configure()
    (put,) = fake.realm_puts
    assert put["attributes"] == {**EXISTING, LIFESPAN_KEY: str(setup_abuse.VERIFY_EMAIL_LIFESPAN)}
    assert fake.realm["attributes"]["clientSessionIdleTimeout"] == "600"
    assert fake.realm["attributes"]["clientSessionMaxLifespan"] == "1200"
    assert fake.realm["registrationFlow"] == setup_abuse.REGISTRATION


def test_a_realm_without_attributes_gets_only_the_lifespan(fake):
    del fake.realm["attributes"]
    _configure()
    assert fake.realm_puts[0]["attributes"] == {LIFESPAN_KEY: str(setup_abuse.VERIFY_EMAIL_LIFESPAN)}


def test_an_attribute_lost_by_the_update_fails_the_run(monkeypatch):
    kc = FakeKeycloak(drop_on_put=("clientSessionIdleTimeout",))
    monkeypatch.setattr(setup_abuse, "Client", lambda base, realm, token: kc)
    with pytest.raises(RuntimeError, match="clientSessionIdleTimeout"):
        _configure()


def test_a_bound_mfa_reset_flow_stays_bound(fake):
    """setup_mfa.py's copy carries the admin TOTP step; rebinding RESET drops it."""
    fake.realm["resetCredentialsFlow"] = MFA_RESET
    fake.flows.append({"alias": MFA_RESET})
    result = _configure()
    assert fake.realm["resetCredentialsFlow"] == MFA_RESET
    assert result["resetCredentialsFlow"] == MFA_RESET
    assert fake.realm["registrationFlow"] == setup_abuse.REGISTRATION


def test_without_mfa_the_protected_reset_flow_is_bound(fake):
    _configure()
    assert fake.realm["resetCredentialsFlow"] == setup_abuse.RESET
