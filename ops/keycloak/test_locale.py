"""Realm i18n import and informal German theme bundle (issues#555).

Static checks, no live Keycloak: every realm JSON that backs computor.at, QA,
integration tests or dev must ship the locales enabled with German as default
(the runtime path in setup_terms.py stays as reconciliation, not as the only
place where this is set), the theme's German login bundle must address
learners informally — no formal "Sie/Ihr/Ihnen" anywhere — and every text the
theme overrides or its sign-in pages show must exist in German and English.
What the theme inherits from stock Keycloak is recorded in
keycloak-stock-messages.json (see keycloak_stock_messages.py).

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

THEME = ROOT / "data" / "keycloak" / "themes" / "computor"
DE_MESSAGES = THEME / "login" / "messages" / "messages_de.properties"
STOCK = json.loads(
    (Path(__file__).resolve().parent / "keycloak-stock-messages.json")
    .read_text(encoding="utf-8")
)
LANGUAGES = ("de", "en")
# Sign-in, one-time code, authenticator setup, password update, info and terms.
PAGES = ["login.ftl", "login-otp.ftl", "login-config-totp.ftl",
         "login-update-password.ftl", "info.ftl", "terms.ftl"]
MSG = re.compile(r"""\bmsg\(\s*["']([^"']+)["']""")
IMPORT = re.compile(r"""<#(?:import|include)\s+"([^"]+\.ftl)\"""")

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


def _bundle(kind: str, language: str) -> dict[str, str]:
    return _properties(THEME / kind / "messages" / f"messages_{language}.properties")


def _resolves(kind: str, language: str, key: str) -> bool:
    """Keycloak finds ``key`` in our bundle or, failing that, in the stock one."""
    return key in _bundle(kind, language) or key in STOCK["bundles"][kind][language]


def _page_keys(name: str, seen: set[str] | None = None) -> set[str]:
    """Message keys of a login template and the templates it imports."""
    seen = set() if seen is None else seen
    if name in seen:
        return set()
    seen.add(name)
    custom = THEME / "login" / name
    if custom.is_file():
        text = custom.read_text(encoding="utf-8")
        keys = {k for k in MSG.findall(text) if "${" not in k}
        imports = IMPORT.findall(text)
    else:
        keys = set(STOCK["templates"][name]["keys"])
        imports = STOCK["templates"][name]["imports"]
    for imported in imports:
        keys |= _page_keys(imported, seen)
    if "requiredAction.*" in keys:
        keys.discard("requiredAction.*")
        keys |= {k for k in STOCK["bundles"]["login"]["en"] if k.startswith("requiredAction.")}
    return keys


def test_stock_record_matches_the_deployed_keycloak() -> None:
    compose = (ROOT / "ops" / "docker" / "docker-compose.keycloak.yaml").read_text(encoding="utf-8")
    deployed = re.search(r"quay\.io/keycloak/keycloak:([^@\s]+)", compose).group(1)
    assert STOCK["keycloak"] == deployed, (
        "keycloak-stock-messages.json records another Keycloak; regenerate it "
        "with ops/keycloak/keycloak_stock_messages.py"
    )


@pytest.mark.parametrize("kind", ["login", "email"])
def test_every_overridden_text_exists_in_both_languages(kind: str) -> None:
    # Our own keys need a text in both bundles, or the other language shows
    # the bare key; a stock key needs at least Keycloak's text there.
    for language in LANGUAGES:
        other = "en" if language == "de" else "de"
        missing = sorted(k for k in _bundle(kind, language) if not _resolves(kind, other, k))
        assert missing == [], f"{kind} messages_{language} keys without {other}: {missing}"


@pytest.mark.parametrize("kind", ["login", "email"])
def test_every_english_override_has_a_german_override(kind: str) -> None:
    # The stock German text is formal; where we reword English, German needs
    # our own wording too.
    missing = sorted(set(_bundle(kind, "en")) - set(_bundle(kind, "de")))
    assert missing == [], f"{kind}: English overrides without German: {missing}"


@pytest.mark.parametrize(
    "page",
    PAGES + sorted(p.name for p in (THEME / "login").glob("*.ftl")),
)
def test_sign_in_page_texts_exist_in_both_languages(page: str) -> None:
    keys = _page_keys(page)
    assert keys, f"{page}: no message keys found"
    for language in LANGUAGES:
        missing = sorted(k for k in keys if not _resolves("login", language, k))
        assert missing == [], f"{page}: no {language} text for {missing}"
