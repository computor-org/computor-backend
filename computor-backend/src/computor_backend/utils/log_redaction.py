"""Redact credential-bearing query parameters before request lines reach logs.

uvicorn logs request targets with their query string: HTTP request lines on
``uvicorn.access`` and WebSocket handshakes (``"WebSocket /ws?token=..."``) on
``uvicorn.error``. Several flows put secrets there: the SSO callback receives
``?code=...&state=...``, the native-app SSO redirect carries
``token``/``refresh_token``, WebSocket clients authenticate with ``?token=``, and
a workspace URL forwarded through /auth/coder-reauth and then the login's
``redirect_uri`` nests such a query once or twice URL-encoded.

Matching is done on *decoded* parameter names (a client may send ``%63ode=``;
the server decodes it to ``code``), case-insensitively, and nested values are
decoded and inspected up to ``_MAX_DEPTH`` levels. A value that is still
encoded after that is treated as uncertain and redacted. Redaction replaces the
whole value of the offending parameter with ``[REDACTED]``.
"""

import logging
import re
from urllib.parse import unquote_plus

_SENSITIVE_KEYS = frozenset({
    "access_token", "refresh_token", "id_token", "token", "code", "state",
    "password", "api_key", "apikey", "client_secret", "secret",
})

REDACTED = "[REDACTED]"

# Levels of URL-encoding looked through. The coder-reauth -> login flow produces
# two; anything deeper is not produced by our flows and is redacted as uncertain.
_MAX_DEPTH = 3

_PIECE_SPLIT = re.compile(r"[?&;#]")
_TOKEN_SPLIT = re.compile(r"(\s+|[\"'<>])")
_QUERY_SPLIT = re.compile(r"([&;#])")


def _is_sensitive_name(name: str) -> bool:
    for _ in range(_MAX_DEPTH + 1):
        decoded = unquote_plus(name)
        if decoded == name:
            return name.strip().lower() in _SENSITIVE_KEYS
        name = decoded
    return True  # still encoded after the depth limit: uncertain


def _has_secret(text: str, depth: int = _MAX_DEPTH) -> bool:
    """True if ``text`` carries a sensitive parameter, at any nesting up to ``depth``."""
    if depth < 0:
        return True  # still encoded after the depth limit: uncertain
    for piece in _PIECE_SPLIT.split(text):
        name, sep, _ = piece.partition("=")
        if sep and _is_sensitive_name(name):
            return True
        decoded = unquote_plus(piece)
        if decoded != piece and _has_secret(decoded, depth - 1):
            return True
    return False


def _redact_piece(piece: str) -> str:
    name, sep, _ = piece.partition("=")
    return f"{name}={REDACTED}" if sep else REDACTED


def _redact_query(query: str) -> str:
    parts = _QUERY_SPLIT.split(query)
    return "".join(
        p if p in ("&", ";", "#") or not _has_secret(p) else _redact_piece(p) for p in parts
    )


def _redact_token(token: str) -> str:
    # Malformed Luna paths/queries may themselves contain learner text. Keep
    # only a fixed route label in HTTP/WS access logs, including encoded paths.
    decoded = unquote_plus(token)
    if re.search(r"(?:^|/)public-luna(?:/|[?#]|$)", decoded):
        return "/public-luna/[REDACTED]"
    if "?" in token:
        base, _, query = token.partition("?")
        return f"{base}?{_redact_query(query)}"
    if "=" in token or "%" in token:
        return _redact_query(token)
    return token


def redact_url(value: str) -> str:
    """Return ``value`` with credential-bearing query parameter values redacted.

    Works on a bare URL/target as well as on a log message that embeds one.
    """
    if "=" not in value and "%" not in value and "public-luna" not in value:
        return value
    return "".join(
        part if _TOKEN_SPLIT.fullmatch(part) else _redact_token(part)
        for part in _TOKEN_SPLIT.split(value)
    )


class RedactQueryCredentialsFilter(logging.Filter):
    """Logging filter that redacts credential query params in a record's message and args.

    Attach it to *handlers* (not loggers) so it also covers records propagated
    from child loggers such as uvicorn.error's WebSocket handshake lines.
    """

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
