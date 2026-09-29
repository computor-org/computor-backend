"""Redact credential-bearing query parameters before request lines reach logs.

uvicorn's access log records the path *with* its query string. Several flows put
secrets there: the SSO callback receives ``?code=...&state=...``, the native-app
SSO redirect carries ``token``/``refresh_token``, and a workspace URL forwarded
through /auth/coder-reauth nests such a query inside ``next`` (URL-encoded). The
filter below rewrites those values to ``[REDACTED]`` while keeping the rest of
the line useful for debugging.
"""

import logging
import re

_SENSITIVE_KEYS = (
    "access_token", "refresh_token", "id_token", "token", "code", "state",
    "password", "api_key", "apikey", "client_secret", "secret",
)

# A sensitive key right after a query delimiter, raw ("?", "&", ";") or
# URL-encoded ("%3F", "%26"), followed by "=" or "%3D". The value runs to the
# next raw "&", "#" or whitespace; for an encoded nested query that swallows the
# rest of the outer parameter, which is the safe direction to err in.
_SENSITIVE_PARAM = re.compile(
    r"(?i)((?:[?&;]|%3F|%26)(?:" + "|".join(_SENSITIVE_KEYS) + r")(?:=|%3D))[^&#\s]*"
)

REDACTED = "[REDACTED]"


def redact_url(value: str) -> str:
    """Return ``value`` with the values of credential-bearing query params redacted."""
    return _SENSITIVE_PARAM.sub(r"\1" + REDACTED, value)


class RedactQueryCredentialsFilter(logging.Filter):
    """Logging filter that redacts credential query params in a record's message and args."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_url(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(redact_url(a) if isinstance(a, str) else a for a in record.args)
        elif isinstance(record.args, dict):
            record.args = {
                k: redact_url(v) if isinstance(v, str) else v for k, v in record.args.items()
            }
        return True
