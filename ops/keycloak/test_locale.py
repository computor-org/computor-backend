"""Realm i18n import and informal German theme bundle (issues#555).

Static checks, no live Keycloak: every realm JSON that backs computor.at, QA,
integration tests or dev must ship the locales enabled with German as default
(the runtime path in setup_terms.py stays as reconciliation, not as the only
place where this is set), and the theme's German login bundle must address
learners informally — no formal "Sie/Ihr/Ihnen" anywhere.

Run: python3 -m pytest ops/keycloak/test_locale.py
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

REALM_JSONS = [
    ROOT / "data" / "keycloak" / "computor-realm.json",
    ROOT / "data" / "keycloak" / "fake-idp-realm.json",
    ROOT / "integration-tests" / "keycloak-import" / "computor-realm.json",
]

DE_MESSAGES = (
    ROOT / "data" / "keycloak" / "themes" / "computor" / "login"
    / "messages" / "messages_de.properties"
)

# Capitalised "Sie/Ihr/Ihnen" is the formal address; the theme speaks "du".
FORMAL = re.compile(r"\b(Sie|Ihr|Ihre|Ihren|Ihres|Ihrer|Ihnen)\b")


def _properties(path: Path) -> dict[str, str]:
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        entries[key.strip()] = value
    return entries


@pytest.mark.parametrize(
    "path", REALM_JSONS, ids=lambda p: str(p.relative_to(ROOT))
)
def test_realm_import_enables_the_locales(path: Path) -> None:
    realm = json.loads(path.read_text(encoding="utf-8"))
    assert realm.get("internationalizationEnabled") is True, (
        f"{path.name}: internationalizationEnabled must be true"
    )
    assert {"de", "en"} <= set(realm.get("supportedLocales") or []), (
        f"{path.name}: supportedLocales must contain de and en"
    )
    assert realm.get("defaultLocale") == "de", (
        f"{path.name}: defaultLocale must be de"
    )


def test_german_login_bundle_has_no_formal_address() -> None:
    formal = {
        key: value
        for key, value in _properties(DE_MESSAGES).items()
        if FORMAL.search(value)
    }
    assert formal == {}, f"formal address in {DE_MESSAGES.name}: {formal}"


def test_german_login_bundle_translates_the_otp_prompt() -> None:
    # login-otp.ftl shows this label; upstream ships it untranslated in the
    # German bundle, which would leave English on a German OTP page.
    entries = _properties(DE_MESSAGES)
    assert entries.get("loginOtpOneTime"), "loginOtpOneTime must be overridden"
    assert entries["loginOtpOneTime"].strip() != "One-time code"
