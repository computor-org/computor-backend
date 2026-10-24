#!/usr/bin/env python3
"""Render the QA Keycloak realm import from data/keycloak/computor-realm.json.

The repository realm is never edited. The QA copy differs from it in what
computor.at changes on its live realm, plus what an isolated stack needs:

- self-registration with email verification and password recovery, the same
  settings the computor.at pilot applies (computor-infra
  prod/configure-public-pilot.sh), so Keycloak 26 runs its email-first signup:
  profile form, verification link, then password setup (issues#441);
- the realm SMTP server is the stack's Mailpit, so no mail leaves the host;
- client secrets substituted like computor.sh does;
- the seeded personas (admin, lecturer, returning learner) with fixed ids,
  verified addresses and passwords from the private credentials file.

Policy that needs the admin API (signup protection, terms, required action
order) is reconciled after start by keycloak_qa_setup.py.

Usage: render_realm.py SOURCE_REALM OUTPUT_FILE PERSONAS_JSON
Env:   KEYCLOAK_CLIENT_SECRET, FORGEJO_KEYCLOAK_CLIENT_SECRET, QA_PUBLIC_ORIGIN,
       QA_MAIL_FROM
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REGISTRATION_SETTINGS = {
    "registrationAllowed": True,
    "verifyEmail": True,
    "resetPasswordAllowed": True,
    "loginWithEmailAllowed": True,
    "duplicateEmailsAllowed": False,
}


def render(source: dict, personas: list[dict], *, client_secret: str,
           forgejo_secret: str, origin: str, mail_from: str) -> dict:
    text = json.dumps(source)
    text = text.replace("PLACEHOLDER_FORGEJO_CLIENT_SECRET", forgejo_secret)
    text = text.replace("PLACEHOLDER_CLIENT_SECRET", client_secret)
    realm = json.loads(text)

    # The stack is reached over an SSH tunnel on plain HTTP.
    realm["sslRequired"] = "none"
    realm.update(REGISTRATION_SETTINGS)
    realm["smtpServer"] = {
        "host": "mailpit",
        "port": "1025",
        "from": mail_from,
        "fromDisplayName": "Computor QA",
        "ssl": "false",
        "starttls": "false",
        "auth": "false",
    }

    callback = f"{origin}/api/auth/keycloak/callback"
    for client in realm.get("clients", []):
        if client.get("clientId") != "computor-backend":
            continue
        redirects = list(client.get("redirectUris", []))
        for uri in (callback, f"{origin}/*"):
            if uri not in redirects:
                redirects.append(uri)
        client["redirectUris"] = redirects
        origins = list(client.get("webOrigins", []))
        if origin not in origins:
            origins.append(origin)
        client["webOrigins"] = origins

    users = []
    for persona in personas:
        user = {
            "id": persona["keycloak_id"],
            "username": persona["username"],
            "enabled": True,
            "email": persona["email"],
            "emailVerified": True,
            "firstName": persona["given_name"],
            "lastName": persona["family_name"],
            "credentials": [
                {"type": "password", "value": persona["password"], "temporary": False}
            ],
            "requiredActions": [],
        }
        if persona.get("groups"):
            user["groups"] = list(persona["groups"])
        users.append(user)
    realm["users"] = users
    return realm


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    source = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    personas = json.loads(Path(argv[3]).read_text(encoding="utf-8"))
    realm = render(
        source,
        personas,
        client_secret=os.environ["KEYCLOAK_CLIENT_SECRET"],
        forgejo_secret=os.environ["FORGEJO_KEYCLOAK_CLIENT_SECRET"],
        origin=os.environ["QA_PUBLIC_ORIGIN"].rstrip("/"),
        mail_from=os.environ.get("QA_MAIL_FROM", "noreply@qa.computor.invalid"),
    )
    output = Path(argv[2])
    tmp = output.with_suffix(".tmp")
    tmp.write_text(json.dumps(realm, indent=2) + "\n", encoding="utf-8")
    # Keycloak reads the import as its image user; the passwords in it are the
    # synthetic QA personas' and also live in the 0600 credentials file.
    os.chmod(tmp, 0o644)
    tmp.replace(output)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
