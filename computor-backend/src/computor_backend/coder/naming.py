"""
Workspace naming helpers.

Coder workspace names must be lowercase alphanumeric/hyphen and short
(~32 chars). These helpers are the single source for that rule, shared by
the API layer (which resolves the effective name before minting the
per-workspace auth token) and the client (as a safety net for direct
callers).
"""

import re

_WORKSPACE_NAME_MAX_LEN = 32


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
