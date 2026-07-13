#!/usr/bin/env python3
"""Stage the Keycloak realm for the integration stack.

Reads the canonical realm (data/keycloak/computor-realm.json), and writes an
import-ready copy that:
  * sets the computor-backend / forgejo client secrets from the environment
    (replacing the PLACEHOLDER_* values), and
  * adds the integration API callback (http://localhost:${IT_API_PORT}/*) to the
    computor-backend client's redirectUris + webOrigins — the canonical realm
    only allows the dev/prod ports (8000/8080/3000), so without this Keycloak
    rejects the integration login dance with 400 "invalid redirect_uri".

The canonical realm is left untouched (dev/prod share it). stdlib only.
"""
import json
import os
import sys

src, dst = sys.argv[1], sys.argv[2]
api_port = os.environ.get("IT_API_PORT", "18000")
kc_secret = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")
fj_secret = os.environ.get("FORGEJO_CLIENT_SECRET", "")

redirect = f"http://localhost:{api_port}/*"
origin = f"http://localhost:{api_port}"

with open(src) as fh:
    realm = json.load(fh)

for client in realm.get("clients", []):
    cid = client.get("clientId")
    if cid == "computor-backend":
        client["secret"] = kc_secret
        ru = client.setdefault("redirectUris", [])
        if redirect not in ru:
            ru.append(redirect)
        wo = client.setdefault("webOrigins", [])
        if origin not in wo:
            wo.append(origin)
    elif cid == "forgejo":
        client["secret"] = fj_secret

# Disable the VERIFY_PROFILE required action. The bootstrap admin
# (ensure_keycloak_admin) is created without firstName/lastName, so Keycloak's
# default profile validation would force a profile-completion form mid-login and
# break the headless authorization-code dance. Test realm only — the canonical
# realm is untouched.
required_actions = realm.setdefault("requiredActions", [])
for alias, name, priority in [("VERIFY_PROFILE", "Verify Profile", 90)]:
    entry = next((a for a in required_actions if a.get("alias") == alias), None)
    if entry is None:
        required_actions.append(
            {
                "alias": alias,
                "name": name,
                "providerId": alias,
                "enabled": False,
                "defaultAction": False,
                "priority": priority,
                "config": {},
            }
        )
    else:
        entry["enabled"] = False
        entry["defaultAction"] = False

os.makedirs(os.path.dirname(dst), exist_ok=True)
with open(dst, "w") as fh:
    json.dump(realm, fh, indent=2)

print(f"Staged Keycloak realm → {dst} (computor-backend redirect += {redirect})")
