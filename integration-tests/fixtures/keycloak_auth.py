"""Headless Keycloak login for integration tests.

Local password auth was removed from the backend — the only way to obtain a
usable bearer token is the SSO authorization-code flow. This module drives that
flow end-to-end with plain httpx (no browser), so scripted test personas can log
in exactly like a real user:

  A. GET  {api}/auth/keycloak/login            -> 302 to the Keycloak authorize URL
  B. GET  {authorize URL}                       -> the Keycloak login form (HTML)
  C. POST {form action} (username, password)    -> 302 to {api}/auth/keycloak/callback?code=...
  D. GET  {callback}                            -> 302 with token/refresh_token in the query
                                                   (+ ct_access_token / ct_refresh_token cookies)

The backend already emits the browser-facing Keycloak host (localhost:${IT_KEYCLOAK_PORT});
we still rewrite the internal host -> public host defensively so this keeps working if
that ever changes. Invite-created users are login-ready immediately (enabled,
emailVerified, non-temporary password, no required actions).

Exposed as pytest fixtures (`keycloak_login`, `authenticate`) and usable standalone.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs, urlparse

import httpx
import pytest


class LoginError(RuntimeError):
    """Raised when the headless login dance fails at any hop."""


@dataclass(frozen=True)
class Credentials:
    token: str
    refresh_token: Optional[str]
    user_id: Optional[str]


def _api_base() -> str:
    return f"http://localhost:{os.environ.get('IT_API_PORT', '18000')}"


def _kc_internal() -> str:
    return os.environ.get("KEYCLOAK_SERVER_URL", "http://keycloak:8080").rstrip("/")


def _kc_public() -> str:
    return f"http://localhost:{os.environ.get('IT_KEYCLOAK_PORT', '18180')}"


def _form_action(html: str) -> str:
    """Extract the login form's POST action from the Keycloak login page."""
    # Prefer the canonical login form; fall back to the first <form> action.
    m = re.search(r'id="kc-form-login"[^>]*\baction="([^"]+)"', html) or re.search(
        r'<form[^>]*\baction="([^"]+)"', html
    )
    if not m:
        raise LoginError("could not find a login form on the Keycloak page")
    return m.group(1).replace("&amp;", "&")


def _error_hint(html: str) -> str:
    m = re.search(r'(?:kc-feedback-text|input-error|error-message)[^>]*>\s*([^<]+)', html)
    return (m.group(1).strip() if m else html[:200]).strip()


def authenticate(
    email: str,
    password: str,
    *,
    api_base: Optional[str] = None,
    provider: str = "keycloak",
    timeout: float = 30.0,
) -> Credentials:
    """Log in via the SSO dance and return a backend bearer token."""
    api_base = (api_base or _api_base()).rstrip("/")
    kc_internal, kc_public = _kc_internal(), _kc_public()

    def _public(url: str) -> str:
        return url.replace(kc_internal, kc_public)

    with httpx.Client(follow_redirects=False, timeout=timeout) as c:
        # A — initiate
        r = c.get(f"{api_base}/auth/{provider}/login")
        if r.status_code != 302:
            raise LoginError(f"initiate login: expected 302, got {r.status_code}: {r.text[:200]}")
        authorize_url = _public(r.headers["location"])

        # B — fetch the login form
        r = c.get(authorize_url)
        if r.status_code != 200:
            raise LoginError(
                f"Keycloak authorize page: expected 200, got {r.status_code} "
                f"(redirect_uri rejected? theme error?): {_error_hint(r.text)}"
            )
        action = _public(_form_action(r.text))

        # C — submit credentials
        r = c.post(action, data={"username": email, "password": password})
        if r.status_code != 302:
            # Keycloak re-renders the form (200) on bad credentials or a required action.
            raise LoginError(f"credentials rejected for {email!r}: {_error_hint(r.text)}")
        callback_url = _public(r.headers["location"])
        if "code=" not in callback_url:
            raise LoginError(f"no authorization code in callback redirect: {callback_url[:200]}")

        # D — backend exchanges the code and mints a session token
        r = c.get(callback_url)
        if r.status_code != 302:
            raise LoginError(f"backend callback: expected 302, got {r.status_code}: {r.text[:200]}")
        q = parse_qs(urlparse(r.headers.get("location", "")).query)
        token = (q.get("token") or [None])[0] or c.cookies.get("ct_access_token")
        if not token:
            raise LoginError("backend callback returned no token")
        return Credentials(
            token=token,
            refresh_token=(q.get("refresh_token") or [None])[0] or c.cookies.get("ct_refresh_token"),
            user_id=(q.get("user_id") or [None])[0],
        )


@pytest.fixture(scope="session")
def keycloak_login():
    """Return the `authenticate(email, password)` callable (one login per call)."""
    return authenticate


@pytest.fixture(scope="session")
def bearer_client_factory(api_base_url: str):
    """Factory: (email, password) -> a session bearer httpx.Client for that user.

    Logs the user in once via the SSO dance and returns a client with the
    Authorization header preset. Callers are responsible for closing clients, or
    use the persona fixtures in `fixtures.clients` which manage lifecycle.
    """
    created: list[httpx.Client] = []

    def _make(email: str, password: str) -> httpx.Client:
        creds = authenticate(email, password, api_base=api_base_url)
        client = httpx.Client(
            base_url=api_base_url,
            headers={"Authorization": f"Bearer {creds.token}"},
            timeout=30.0,
        )
        client.creds = creds  # type: ignore[attr-defined]
        created.append(client)
        return client

    yield _make
    for client in created:
        client.close()
