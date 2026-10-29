"""
Resolve the learner's reading language once, server-side.

One reading language ("de" or "en") for UI and content:

  - the profile language wins when it is ``de`` or ``en``;
  - otherwise the first ``Accept-Language`` entry by q-value order decides
    (only the primary subtag matters: ``de-AT`` -> ``de``);
  - any other language maps to ``en``;
  - a missing or empty header maps to ``de`` (German-first instance).

Endpoints return this as ``effective_language`` so every client (web,
workspace dashboard, VS Code extension) shows the same language without
each re-deriving it — see computor-org/issues#549.
"""
from typing import Optional

SUPPORTED_LANGUAGES = ("de", "en")
DEFAULT_LANGUAGE = "de"


def resolve_effective_language(
    profile_language: Optional[str],
    accept_language: Optional[str],
) -> str:
    """Resolve the reading language from the profile and the request header.

    Pure: no I/O, no session state. ``profile_language`` is the stored
    ``profile.language_code`` (null when the user never chose one).
    """
    if profile_language in SUPPORTED_LANGUAGES:
        return profile_language

    if not accept_language or not accept_language.strip():
        return DEFAULT_LANGUAGE

    best_q: Optional[float] = None
    best_tag = ""
    for entry in accept_language.split(","):
        tag, _, params = entry.partition(";")
        q = 1.0
        for param in params.split(";"):
            key, _, value = param.partition("=")
            if key.strip().lower() == "q":
                try:
                    q = float(value)
                except ValueError:
                    q = 0.0
        # Strict > keeps the earliest entry when q-values tie.
        if best_q is None or q > best_q:
            best_q, best_tag = q, tag.strip().lower()

    primary = best_tag.split("-", 1)[0]
    return primary if primary in SUPPORTED_LANGUAGES else "en"
