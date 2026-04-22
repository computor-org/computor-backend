#!/usr/bin/env python3
"""Create a GitLab admin PAT and write it into `.env.integration`.

Runs once after `make up`. Idempotent: if a usable token already lives in
`.env.integration`, we keep it. Otherwise we log in as root with the
initial password, mint a new PAT with the scopes the API needs, and
persist it.

Invoked from the Makefile via `make bootstrap`.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env.integration"

TOKEN_NAME = "integration-test-admin"
TOKEN_SCOPES = ["api", "read_api", "read_repository", "write_repository", "sudo"]


def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        sys.exit(f"Missing {path} — run `make env` first.")
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def write_env_value(path: Path, key: str, value: str) -> None:
    content = path.read_text()
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    replacement = f"{key}={value}"
    if pattern.search(content):
        content = pattern.sub(replacement, content)
    else:
        content = content.rstrip() + "\n" + replacement + "\n"
    path.write_text(content)


def gitlab_url(env: dict[str, str]) -> str:
    port = env.get("IT_GITLAB_HTTP_PORT", "8085")
    return f"http://localhost:{port}"


def token_is_valid(base: str, token: str) -> bool:
    try:
        r = requests.get(
            f"{base}/api/v4/user",
            headers={"PRIVATE-TOKEN": token},
            timeout=5,
        )
        return r.status_code == 200
    except requests.RequestException:
        return False


def oauth_login(base: str, password: str) -> str:
    r = requests.post(
        f"{base}/oauth/token",
        json={"grant_type": "password", "username": "root", "password": password},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def get_root_user_id(base: str, oauth_token: str) -> int:
    r = requests.get(
        f"{base}/api/v4/user",
        headers={"Authorization": f"Bearer {oauth_token}"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["id"]


def create_pat(base: str, oauth_token: str, user_id: int) -> str:
    # GitLab 16+ requires an expiry; one year out is plenty for a test stack.
    r = requests.post(
        f"{base}/api/v4/users/{user_id}/personal_access_tokens",
        headers={"Authorization": f"Bearer {oauth_token}"},
        json={
            "name": TOKEN_NAME,
            "scopes": TOKEN_SCOPES,
            "expires_at": "2099-12-31",
        },
        timeout=30,
    )
    if r.status_code >= 400:
        sys.exit(f"PAT creation failed ({r.status_code}): {r.text}")
    return r.json()["token"]


def main() -> int:
    env = read_env(ENV_FILE)
    base = gitlab_url(env)

    existing = env.get("GITLAB_ADMIN_TOKEN", "").strip()
    if existing and token_is_valid(base, existing):
        print(f"GITLAB_ADMIN_TOKEN already valid for {base}; nothing to do.")
        return 0

    root_password = env.get("GITLAB_ROOT_PASSWORD")
    if not root_password:
        sys.exit("GITLAB_ROOT_PASSWORD missing from .env.integration.")

    print(f"Logging into {base} as root…")
    oauth = oauth_login(base, root_password)
    user_id = get_root_user_id(base, oauth)

    print("Creating admin PAT…")
    token = create_pat(base, oauth, user_id)

    write_env_value(ENV_FILE, "GITLAB_ADMIN_TOKEN", token)
    print(f"GITLAB_ADMIN_TOKEN written to {ENV_FILE}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
