"""Error messages in the reader's language.

The API answers errors with ``message`` in the request's reading language
(profile language, else Accept-Language; see ``utils/reading_language.py``),
``message_en`` with the English original for logs and old clients, and
``title`` as the short heading of the error code. Only German is translated;
any other reading language gets the English text.
"""

import re
import time
from functools import lru_cache
from typing import Optional

from computor_backend.exceptions import messages_de
from computor_backend.utils.reading_language import resolve_effective_language

# Single braces only: "{{x}}" is a literal brace pair, as in str.format.
_PLACEHOLDER = re.compile(r"(?<!\{)\{(\w+)\}(?!\})")


@lru_cache(maxsize=1)
def _templates() -> list:
    """Templates with variable parts as (regex, German), most specific first."""
    compiled = []
    for english, german in messages_de.DETAILS.items():
        if not _PLACEHOLDER.search(english):
            continue
        pattern, last = "", 0
        for match in _PLACEHOLDER.finditer(english):
            pattern += re.escape(english[last:match.start()].replace("{{", "{").replace("}}", "}"))
            pattern += f"(?P<{match.group(1)}>.+?)"
            last = match.end()
        pattern += re.escape(english[last:].replace("{{", "{").replace("}}", "}"))
        literal = len(_PLACEHOLDER.sub("", english))
        compiled.append((literal, re.compile(f"^{pattern}$", re.DOTALL), german))
    compiled.sort(key=lambda item: -item[0])
    return [(regex, german) for _, regex, german in compiled]


@lru_cache(maxsize=1)
def _exact() -> dict:
    return {
        english.replace("{{", "{").replace("}}", "}"): german.replace("{{", "{").replace("}}", "}")
        for english, german in messages_de.DETAILS.items()
        if not _PLACEHOLDER.search(english)
    }


def _translate_one(text: str) -> Optional[str]:
    exact = _exact().get(text)
    if exact is not None:
        return exact
    for regex, german in _templates():
        match = regex.match(text)
        if match:
            return german.format(**match.groupdict())
    return None


def translate_detail_de(text: str) -> Optional[str]:
    """German for an English detail, or ``None`` when there is none.

    A refusal may be one known sentence followed by another (a reason and a
    hint), so a text that matches no entry as a whole is tried as two parts
    split after a sentence end.
    """
    text = text.strip()
    whole = _translate_one(text)
    if whole is not None:
        return whole
    for match in re.finditer(r"[.!?] ", text):
        head, tail = text[:match.start() + 1], text[match.end():]
        head_de, tail_de = _translate_one(head), _translate_one(tail)
        if head_de is not None and tail_de is not None:
            return f"{head_de} {tail_de}"
    return None


def localize_message(message: str, error_code: Optional[str], default_en: Optional[str], language: str) -> str:
    """``message`` in ``language``, or unchanged when no translation exists."""
    if language != "de" or not message:
        return message
    if error_code and message == default_en and error_code in messages_de.CODES:
        return messages_de.CODES[error_code][1]
    return translate_detail_de(message) or message


def localize_title(title: Optional[str], error_code: Optional[str], language: str) -> Optional[str]:
    if language == "de" and error_code in messages_de.CODES:
        return messages_de.CODES[error_code][0]
    return title


# Profile languages change rarely; a short cache keeps error responses from
# costing a database round trip each.
_PROFILE_TTL_SECONDS = 60.0
_profile_cache: dict = {}


def _profile_language(user_id: Optional[str]) -> Optional[str]:
    if not user_id:
        return None
    now = time.monotonic()
    cached = _profile_cache.get(user_id)
    if cached and cached[1] > now:
        return cached[0]
    try:
        from computor_backend.database import get_db_session
        from computor_backend.model.auth import Profile

        with get_db_session() as db:
            language = (
                db.query(Profile.language_code)
                .filter(Profile.user_id == user_id)
                .scalar()
            )
    except Exception:
        # An error response must never fail on its own language lookup.
        return None
    if len(_profile_cache) > 10_000:
        _profile_cache.clear()
    _profile_cache[user_id] = (language, now + _PROFILE_TTL_SECONDS)
    return language


def request_language(request) -> str:
    """Reading language of the request that raised the error."""
    state = getattr(request, "state", None)
    user_id = getattr(state, "user_id", None) if state is not None else None
    headers = getattr(request, "headers", None) or {}
    return resolve_effective_language(
        _profile_language(str(user_id) if user_id else None),
        headers.get("Accept-Language") or headers.get("accept-language"),
    )


def scope_language(scope) -> str:
    """Reading language for a middleware refusal, which runs before sign-in
    and so knows only the Accept-Language header."""
    for name, value in scope.get("headers") or []:
        if name.lower() == b"accept-language":
            return resolve_effective_language(None, value.decode("latin-1"))
    return resolve_effective_language(None, None)
