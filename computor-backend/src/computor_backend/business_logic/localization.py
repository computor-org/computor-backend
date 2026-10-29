"""Per-language titles and descriptions (computor-org/issues#550).

``title``/``description`` stay the source text that old clients read. The
optional ``title_i18n``/``description_i18n`` maps, keyed by language code, hold
other languages; a client that sends ``?localize=<de|en>`` gets the entry for
that language in ``title``/``description`` and the source text where there is
none.
"""

from typing import Annotated, Any, Dict, Optional, Tuple

from fastapi import Query

LocalizeParam = Annotated[
    Optional[str],
    Query(
        description="Reading language (de, en) whose title and description replace "
        "the source text; a language without an entry keeps the source text",
    ),
]


def i18n_map(value: Any) -> Optional[Dict[str, str]]:
    """``value`` as a ``{language code: text}`` map, or None if it holds none."""
    # meta.yaml and course files are hand-written; drop what is not text.
    if not isinstance(value, dict):
        return None
    cleaned = {str(k): v for k, v in value.items() if isinstance(v, str)}
    return cleaned or None


def localized_text(mapping: Any, lang: Optional[str], source: Optional[str]) -> Optional[str]:
    """The entry for ``lang`` in ``mapping``, or ``source`` if there is none."""
    if not lang or not isinstance(mapping, dict):
        return source
    value = mapping.get(lang)
    # A blank entry is a missing translation, not a blank title.
    if not isinstance(value, str) or not value.strip():
        return source
    return value


def localize(obj: Any, lang: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """The ``(title, description)`` a reader of ``lang`` should see for ``obj``."""
    return (
        localized_text(getattr(obj, "title_i18n", None), lang, getattr(obj, "title", None)),
        localized_text(getattr(obj, "description_i18n", None), lang, getattr(obj, "description", None)),
    )


def localize_dto(dto: Any, lang: Optional[str]) -> Any:
    """``dto`` with title and description resolved for ``lang``; unchanged without ``lang``."""
    if not lang or dto is None:
        return dto
    title, description = localize(dto, lang)
    # A copy: cached DTOs are shared between requests and readers.
    return dto.model_copy(update={"title": title, "description": description})
