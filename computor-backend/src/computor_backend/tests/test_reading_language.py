"""Unit tests for the single reading-language resolution (issues#549)."""
import pytest

from computor_backend.utils.reading_language import resolve_effective_language


@pytest.mark.parametrize("profile_language,accept_language,expected", [
    # An explicit profile choice wins over any header.
    ("de", "en-US,en;q=0.9", "de"),
    ("en", "de-AT,en;q=0.5", "en"),
    # No profile choice: the first entry by q-value order decides.
    (None, "en-US,en;q=0.9,de;q=0.8", "en"),
    (None, "fr-FR,de;q=0.5", "en"),
    (None, "de-AT,en;q=0.5", "de"),
    # Only the primary subtag matters.
    (None, "de-CH", "de"),
    # Any other language maps to English.
    (None, "fr-FR", "en"),
    (None, "it;q=1.0,de;q=0.9", "en"),
    # No header at all (or an empty one): German-first default.
    (None, None, "de"),
    (None, "", "de"),
    # A profile language outside de/en is not a choice; fall back to header.
    ("fr", "de-DE", "de"),
    ("fr", None, "de"),
])
def test_resolve_effective_language(profile_language, accept_language, expected):
    assert resolve_effective_language(profile_language, accept_language) == expected


def test_q_value_order_beats_header_order():
    # "de" carries the higher q, so it wins although "en" is listed first.
    assert resolve_effective_language(None, "en;q=0.3,de;q=0.8") == "de"
