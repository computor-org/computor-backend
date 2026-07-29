"""
Workspace and username naming helpers.

Coder workspace names must be lowercase alphanumeric/hyphen and short
(~32 chars). These helpers are the single source for that rule, shared by
the API layer (which resolves the effective name before minting the
per-workspace auth token) and the client (as a safety net for direct
callers).

Coder *usernames* have the same character rules plus "must start with a
letter", and Computor only has UUIDs to name users by. The obvious encoding,
``"u" + str(uuid)``, is 37 characters and so used to be truncated to 32 —
silently dropping the last five characters of the UUID. That made the mapping
one-way: every consumer had to match user ids by *prefix*, and anything
deriving a value from the username (the workspace app secret) derived it from
a different string than the provisioning side did.

Base32 of the UUID's 16 raw bytes is 26 characters, so ``"u" + base32`` is 27 —
inside the limit, still lowercase alphanumeric, still letter-initial, and
**bijective**: ``decode_coder_username`` inverts it exactly. No prefix matching
anywhere, and no way to derive a secret from a lossy name.

The ``"u"`` prefix is kept deliberately: ForwardAuth uses it to tell a regular
user's workspace from Coder's own ``admin`` account, which has no Computor user.
"""

import base64
import re
import uuid as uuid_mod
from typing import Optional

_WORKSPACE_NAME_MAX_LEN = 32

# 16 raw bytes -> 26 base32 characters (+ "======" padding, which we strip).
_USERNAME_B32_LEN = 26
_USERNAME_LEN = 1 + _USERNAME_B32_LEN


def sanitize_workspace_name(name: str) -> str:
    """Sanitize a workspace name for Coder (NO 'u' prefix - that's usernames only)."""
    return re.sub(r"[^a-z0-9-]", "", name.lower())[:_WORKSPACE_NAME_MAX_LEN].strip("-")


def derive_workspace_name(template_name: str) -> str:
    """Default workspace name for a template: 'python-workspace' -> 'python'.

    Workspace names are scoped per user, so one workspace per template is the
    natural default; the '-workspace' suffix would only repeat what the
    context already says.
    """
    base = template_name.lower()
    if base.endswith("-workspace"):
        base = base[: -len("-workspace")]
    return sanitize_workspace_name(base) or "workspace"


def encode_coder_username(user_id: str) -> str:
    """The Coder username for a Computor user id: ``u`` + base32 of its bytes.

    27 characters, lowercase alphanumeric, letter-initial, and reversible with
    ``decode_coder_username``. Ids that are not UUIDs (tests, fixtures) fall
    back to a sanitising rule so they still produce a name Coder accepts — they
    are not part of any addressing scheme.
    """
    try:
        uid = uuid_mod.UUID(str(user_id))
    except (ValueError, AttributeError, TypeError):
        return _sanitize_non_uuid(str(user_id))
    return "u" + base64.b32encode(uid.bytes).decode("ascii").lower().rstrip("=")


def decode_coder_username(username: Optional[str]) -> Optional[str]:
    """The Computor user id behind a Coder username, or None.

    None for anything that is not one of our encoded names — Coder's ``admin``
    account, an owner we did not create, malformed input.
    """
    if not username or len(username) != _USERNAME_LEN or not username.startswith("u"):
        return None
    try:
        raw = base64.b32decode(username[1:].upper() + "======")
    except Exception:
        return None
    if len(raw) != 16:
        return None
    try:
        return str(uuid_mod.UUID(bytes=raw))
    except (ValueError, TypeError):
        return None


def coder_username_matches_user(username: Optional[str], user_id: str) -> bool:
    """Does this Coder owner name belong to this Computor user?

    Exact both ways: the name decodes to the user id, or it *is* the bare user
    id (internal callers and tests address workspaces that way). Nothing
    partial — a prefix match here would let one user reach another's workspace
    whenever their ids share a leading run.
    """
    if not username:
        return False
    uid = str(user_id)
    if username == uid:
        return True
    return decode_coder_username(username) == uid


def _sanitize_non_uuid(username: str) -> str:
    """Coder-safe name for an id that is not a UUID. Never used for addressing."""
    clean = re.sub(r"[^a-z0-9-]", "", username.lower())
    return ("u" + clean)[:_WORKSPACE_NAME_MAX_LEN].rstrip("-")
