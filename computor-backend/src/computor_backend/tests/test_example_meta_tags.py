"""Unit tests for the meta.yaml -> Example tags/category mapping on upload.

The Examples view offers Category and Tags as filters, but nothing ever filled
either column: ``category`` was never written at all, and ``tags`` came only
from a ``tags:`` key that is not part of the documented meta.yaml format, while
the documented ``keywords`` field was read by no one — so both filters filtered
over columns that stayed empty (computor-org/issues#358).

``keywords`` is the source now. ``tags`` keeps working for the examples that
already carry it, but must not win over keywords, or an example with both would
silently ignore the field the schema documents.
"""
import pytest

from computor_backend.api.examples import _as_string_list


class TestAsStringList:
    def test_keeps_the_order_the_lecturer_wrote(self):
        assert _as_string_list(["loops", "arrays", "beginner"]) == [
            "loops",
            "arrays",
            "beginner",
        ]

    def test_trims_whitespace(self):
        assert _as_string_list(["  loops  ", "arrays\n"]) == ["loops", "arrays"]

    def test_drops_duplicates_and_blanks(self):
        assert _as_string_list(["loops", "", "loops", "   ", None, "arrays"]) == [
            "loops",
            "arrays",
        ]

    def test_accepts_a_lone_scalar(self):
        assert _as_string_list("loops") == ["loops"]

    def test_stringifies_non_strings(self):
        assert _as_string_list([2027, True]) == ["2027", "True"]

    @pytest.mark.parametrize("value", [None, [], "", "   ", [None, "  "]])
    def test_nothing_worth_storing_is_no_tags(self, value):
        assert _as_string_list(value) == []


class TestUploadTagSource:
    """The precedence the upload endpoint applies, spelled out.

    Mirrors ``tags = _as_string_list(meta.get('keywords')) or
    _as_string_list(meta.get('tags'))`` — kept here so a change to that line
    has to be a deliberate one.
    """

    @staticmethod
    def tags_for(meta: dict) -> list[str]:
        return _as_string_list(meta.get("keywords")) or _as_string_list(meta.get("tags"))

    def test_keywords_become_the_tags(self):
        assert self.tags_for({"keywords": ["loops", "arrays"]}) == ["loops", "arrays"]

    def test_a_legacy_tags_key_still_works(self):
        assert self.tags_for({"tags": ["legacy"]}) == ["legacy"]

    def test_keywords_win_over_a_legacy_tags_key(self):
        assert self.tags_for({"keywords": ["documented"], "tags": ["legacy"]}) == [
            "documented"
        ]

    def test_empty_keywords_fall_through_to_tags(self):
        assert self.tags_for({"keywords": [], "tags": ["legacy"]}) == ["legacy"]

    def test_an_example_with_neither_has_no_tags(self):
        assert self.tags_for({"title": "Quadratic equation"}) == []
