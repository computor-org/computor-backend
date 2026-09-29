"""Unit tests for the access-log credential redaction filter."""

import logging

import pytest

from computor_backend.utils.log_redaction import RedactQueryCredentialsFilter, redact_url

CODE = "lr_code_3f8a1c6e0d92"
STATE = "lr_state_a0b7e4d15c68"
ACCESS = "lr_access_9d2e6b0f41c7"
REFRESH = "lr_refresh_57c1a8e3d06b"


def _access_record(path):
    # Same shape uvicorn.access emits: (client, method, path+query, http_ver, status).
    return logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 1,
        '%s - "%s %s HTTP/%s" %d', ("10.0.0.1:1234", "GET", path, "1.1", 302), None,
    )


@pytest.mark.parametrize(
    "path",
    [
        f"/auth/keycloak/callback?code={CODE}&state={STATE}",
        f"/auth/success?user_id=u&token={ACCESS}&refresh_token={REFRESH}",
        f"/coder/uabc/ws/?TOKEN={ACCESS}&Refresh_Token={REFRESH}#x",
        # A workspace URL nested (URL-encoded) in /auth/coder-reauth?next=...
        f"/auth/coder-reauth?next=%2Fcoder%2Fuabc%2Fws%2F%3Ftoken%3D{ACCESS}%26refresh_token%3D{REFRESH}",
    ],
)
def test_access_log_line_has_no_credentials(path):
    record = _access_record(path)
    assert RedactQueryCredentialsFilter().filter(record) is True
    line = record.getMessage()
    for secret in (CODE, STATE, ACCESS, REFRESH):
        assert secret not in line
    assert "[REDACTED]" in line
    assert path.split("?", 1)[0] in line  # the route stays readable


def test_non_credential_params_are_kept():
    assert redact_url("/api/items?page=2&codename=x&mytoken=y") == "/api/items?page=2&codename=x&mytoken=y"
