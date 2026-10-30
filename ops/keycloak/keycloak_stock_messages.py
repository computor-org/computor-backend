"""Record what our Keycloak theme inherits from the stock themes (issues#555).

ops/keycloak/test_locale.py checks that every sign-in page text exists in
German and English. Pages the computor theme does not replace come from
Keycloak's stock templates, and keys it does not override come from Keycloak's
stock message bundles; neither is in this repository. This script reads them
from the keycloak-themes jar of the pinned Keycloak image and writes
keycloak-stock-messages.json next to it:

- the message keys and imports of the stock login templates the tests need,
- which of the keys our theme overrides or our pages use exist in the stock
  German and English bundles.

Regenerate after a Keycloak upgrade or a change to the theme's messages:

    cid=$(docker create quay.io/keycloak/keycloak:<version>)
    docker cp "$cid:/opt/keycloak/lib/lib/main/org.keycloak.keycloak-themes-<version>.jar" /tmp/themes.jar
    docker rm "$cid"
    python3 ops/keycloak/keycloak_stock_messages.py <version> /tmp/themes.jar
"""

import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEME = ROOT / "data" / "keycloak" / "themes" / "computor"
OUTPUT = Path(__file__).resolve().parent / "keycloak-stock-messages.json"

# login.ftl also serves the username/password page; login-otp.ftl the one-time
# code, login-config-totp.ftl the authenticator setup.
PAGES = ["login.ftl", "login-otp.ftl", "login-config-totp.ftl",
         "login-update-password.ftl", "info.ftl", "terms.ftl"]

MSG = re.compile(r"""\bmsg\(\s*["']([^"']+)["']""")
IMPORT = re.compile(r"""<#(?:import|include)\s+"([^"]+\.ftl)\"""")
# Keys built at run time; the parts are the values Keycloak can insert.
DYNAMIC = {
    'loginTotp." + totp.policy.type': ["loginTotp.totp", "loginTotp.hotp"],
}


def template_entry(text: str) -> dict:
    keys = set()
    for key in MSG.findall(text):
        if "${messageHeader}" in key:
            continue  # the header is itself a message key chosen by the server
        if key.startswith("requiredAction."):
            continue  # expanded from the bundle below
        keys.add(key)
    for pattern, expansion in DYNAMIC.items():
        if pattern in text:
            keys.discard(pattern.split('"')[0])
            keys.update(expansion)
    if "requiredAction.${" in text:
        keys.add("requiredAction.*")
    return {"imports": sorted(set(IMPORT.findall(text))), "keys": sorted(keys)}


def properties(text: str) -> dict:
    entries = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        entries[key.strip()] = value
    return entries


def main(version: str, jar_path: str) -> None:
    jar = zipfile.ZipFile(jar_path)

    def stock(path: str) -> str:
        return jar.read(f"theme/{path}").decode("utf-8")

    templates = {}
    custom = {p.name for p in (THEME / "login").glob("*.ftl")}
    pending = list(PAGES) + [
        name for p in (THEME / "login").glob("*.ftl")
        for name in IMPORT.findall(p.read_text(encoding="utf-8"))
    ]
    while pending:
        name = pending.pop()
        if name in templates or name in custom:
            continue
        templates[name] = template_entry(stock(f"base/login/{name}"))
        pending.extend(templates[name]["imports"])

    bundles = {}
    for kind in ("login", "email"):
        ours = set()
        for language in ("de", "en"):
            ours |= properties((THEME / kind / "messages" / f"messages_{language}.properties")
                               .read_text(encoding="utf-8")).keys()
        if kind == "login":
            ours |= {k for t in templates.values() for k in t["keys"]}
            ours |= {k for p in (THEME / "login").glob("*.ftl")
                     for k in MSG.findall(p.read_text(encoding="utf-8"))}
        bundles[kind] = {}
        for language in ("de", "en"):
            # The keycloak theme sits between ours and base; both may define keys.
            stock_keys = set()
            for theme in ("base", "keycloak"):
                try:
                    stock_keys |= properties(stock(f"{theme}/{kind}/messages/messages_{language}.properties")).keys()
                except KeyError:
                    pass
            present = ours & stock_keys
            present |= {k for k in stock_keys if k.startswith("requiredAction.")} if kind == "login" else set()
            bundles[kind][language] = sorted(present)

    OUTPUT.write_text(json.dumps({"keycloak": version, "templates": dict(sorted(templates.items())),
                                  "bundles": bundles}, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:3])
