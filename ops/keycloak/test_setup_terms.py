"""Ordering guarantees of setup_terms.py (PR #244 review, finding 3).

A fake Keycloak admin API records every write. The property under test: the
TERMS_AND_CONDITIONS required action is enabled only after both locales'
texts are stored and read back identical; any failure before that leaves it
disabled. Run: python3 -m pytest ops/keycloak/test_setup_terms.py
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import setup_terms  # noqa: E402

TEXTS = json.loads(setup_terms.TEXTS_FILE.read_text(encoding="utf-8"))


class FakeKeycloak:
    """Minimal in-memory stand-in for the endpoints setup_terms.py uses."""

    def __init__(self, fail_put_key=None, corrupt_on_read=None):
        self.realm = {"realm": "computor", "internationalizationEnabled": False}
        self.localization = {"de": {}, "en": {}}
        self.action = {"alias": "TERMS_AND_CONDITIONS", "providerId": "TERMS_AND_CONDITIONS",
                       "enabled": False, "defaultAction": False}
        self.fail_put_key = fail_put_key
        self.corrupt_on_read = corrupt_on_read
        self.writes = []

    def request(self, method, url, token=None, json_body=None, form_body=None):
        path = url.split("/admin/realms/computor", 1)[1]
        if method == "GET":
            if path == "/authentication/required-actions":
                return 200, [dict(self.action)]
            if path == "":
                return 200, dict(self.realm)
            if path.startswith("/users"):
                return 200, [{"id": "u1", "username": "someone",
                              "requiredActions": ["UPDATE_PASSWORD"]}]
            if path.startswith("/localization/"):
                locale = path.rsplit("/", 1)[1]
                stored = dict(self.localization[locale])
                if self.corrupt_on_read and self.corrupt_on_read in stored:
                    stored[self.corrupt_on_read] = "Terms and conditions to be defined"
                return 200, stored
        self.writes.append((method, path))
        if path == "":
            self.realm = json_body
            return 204, None
        if path.startswith("/authentication/required-actions/"):
            self.action = json_body
            return 204, None
        return 404, None

    def raw_text(self, method, url, token, text):
        path = url.split("/admin/realms/computor", 1)[1]
        self.writes.append((method, path))
        _, _, locale, key = path.split("/")
        if key == self.fail_put_key:
            return 500, b"boom"
        self.localization[locale][key] = text
        return 204, b""


@pytest.fixture
def run(monkeypatch):
    def _run(fake, *argv):
        monkeypatch.setattr(setup_terms, "_request", fake.request)
        monkeypatch.setattr(setup_terms, "_raw_text_request", fake.raw_text)
        monkeypatch.setattr(setup_terms, "get_admin_token", lambda *a: "token")
        monkeypatch.setenv("COMPUTOR_LEGAL_PROFILE", "computor-at")
        monkeypatch.setenv("KEYCLOAK_ADMIN", "admin")
        monkeypatch.setenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
        monkeypatch.setattr(sys, "argv", ["setup_terms.py", *argv])
        setup_terms.main()

    return _run


def _enabled(fake):
    return fake.action.get("enabled") and fake.action.get("defaultAction")


def test_texts_are_installed_before_the_action_is_enabled(run):
    fake = FakeKeycloak()
    run(fake)
    assert _enabled(fake)
    enable = fake.writes.index(("PUT", "/authentication/required-actions/TERMS_AND_CONDITIONS"))
    text_writes = [i for i, (_, p) in enumerate(fake.writes) if p.startswith("/localization/")]
    assert len(text_writes) == 2 * len(TEXTS["de"])
    assert max(text_writes) < enable
    assert fake.localization["de"]["termsTitle"] == TEXTS["de"]["termsTitle"]


def test_second_run_writes_nothing(run):
    fake = FakeKeycloak()
    run(fake)
    fake.writes.clear()
    run(fake)
    assert fake.writes == []


def test_failed_text_write_leaves_the_action_disabled(run):
    fake = FakeKeycloak(fail_put_key="termsText")
    with pytest.raises(SystemExit):
        run(fake)
    assert not _enabled(fake)


def test_text_that_does_not_read_back_leaves_the_action_disabled(run):
    fake = FakeKeycloak(corrupt_on_read="termsText")
    with pytest.raises(SystemExit, match="NOT enabled"):
        run(fake)
    assert not _enabled(fake)


def test_dry_run_writes_nothing(run):
    fake = FakeKeycloak()
    run(fake, "--dry-run")
    assert fake.writes == []
    assert not _enabled(fake)


def test_no_user_is_ever_modified(run):
    """Finding 2: no bulk rewrite of requiredActions from a listing snapshot."""
    fake = FakeKeycloak()
    run(fake)
    with pytest.raises(SystemExit):  # the old bulk option is gone (argparse error)
        run(fake, "--require-for-existing-users")
    assert not any(p.startswith("/users") for _, p in fake.writes)
