"""
Generate Forgejo/Keycloak-safe usernames (handles) from a user's name or email.

Usernames are system-generated, never user-chosen. The handle becomes the
Keycloak ``username`` (hence the OIDC ``preferred_username``), which Forgejo
consumes as its account name on first login. It must therefore satisfy
Forgejo's username rules and avoid Forgejo's reserved route names.

Forgejo (Gitea) username rules:
  - allowed chars: ASCII letters, digits, and ``-`` ``_`` ``.``
  - may not start/end with a non-alphanumeric char, and may not contain ``..``
  - uniqueness is case-insensitive; we always emit lowercase
  - must not collide with a reserved route name (admin, api, ...)

This module is pure (no I/O): it returns an *ordered list of candidates*,
most-preferred first. Uniqueness is resolved by the caller against Keycloak
(see ``KeycloakAdminClient.generate_unique_username``).

Examples:
    >>> username_candidates("Max", "Mustermann")[0]
    'mmusterm'
    >>> username_candidates(None, "Smith")[0]
    'smith'
    >>> username_candidates(None, None, "jane.doe@example.com")[0]
    'jane.doe'
"""
from typing import List, Optional

from text_unidecode import unidecode

# Forgejo/Gitea reserved usernames (built-in routes & special names), lowercased.
# A generated handle that lands here gets a numeric suffix instead.
FORGEJO_RESERVED = {
    "admin", "api", "assets", "attachments", "avatar", "avatars", "captcha",
    "commits", "debug", "devtest", "error", "explore", "favicon.ico", "ghost",
    "help", "install", "issues", "login", "logout", "manifest.json", "metrics",
    "milestones", "new", "notifications", "org", "pulls", "raw", "repo",
    "robots.txt", "search", "security", "serviceworker.js", "signin", "signup",
    "ssh_info", "stars", "swagger.v1.json", "template", "user", "users", "v2",
}

# Forgejo's default max username length is 40; stay comfortably under it.
_MAX_LEN = 30


def normalize_name_for_username(name: Optional[str]) -> str:
    """Lowercase, transliterate to ASCII, and keep only ``[a-z0-9]``.

    >>> normalize_name_for_username("Müller")
    'muller'
    >>> normalize_name_for_username("José García")
    'josegarcia'
    """
    if not name:
        return ""
    name = unidecode(name.lower())
    return "".join(c for c in name if c.isalnum() and c.isascii())


def _sanitize(handle: str) -> str:
    """Coerce an arbitrary string into a Forgejo-valid handle (or ``''``)."""
    handle = unidecode(handle.lower())
    handle = "".join(
        c if ((c.isalnum() and c.isascii()) or c in "-_.") else "" for c in handle
    )
    # Forgejo forbids consecutive dots.
    while ".." in handle:
        handle = handle.replace("..", ".")
    # No leading/trailing separators.
    handle = handle.strip("-_.")
    return handle[:_MAX_LEN]


def _avoid_reserved(handle: str) -> str:
    return f"{handle}1" if handle.lower() in FORGEJO_RESERVED else handle


def username_candidates(
    given_name: Optional[str],
    family_name: Optional[str],
    email: Optional[str] = None,
    target_length: int = 8,
) -> List[str]:
    """Return ordered Forgejo-safe handle candidates, most preferred first.

    Strategy:
      1. first initial + truncated family name      -> "mmusterm"
      2. progressively more of the given name        -> "mamusterm", "maxmusterm"
      3. full given + family
      4. email local-part
      5. "user" (last resort, never empty)

    The caller checks each against Keycloak and takes the first free one,
    appending a numeric suffix if every candidate collides.
    """
    given = normalize_name_for_username(given_name)
    family = normalize_name_for_username(family_name)

    candidates: List[str] = []

    def add(raw: str) -> None:
        handle = _avoid_reserved(_sanitize(raw))
        if handle and handle not in candidates:
            candidates.append(handle)

    if given and family:
        for n in range(1, len(given) + 1):
            fam = target_length - n
            fam = fam if fam >= 1 else len(family)
            add(given[:n] + family[:fam])
        add(given + family)
    elif family:
        add(family[:target_length])
        add(family)
    elif given:
        add(given[:target_length])
        add(given)

    if email and "@" in email:
        add(email.split("@")[0])

    if not candidates:
        candidates.append("user")

    return candidates
