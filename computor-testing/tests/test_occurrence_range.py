"""Unit tests for structural occurrence counting and range semantics.

Two things are covered:

``resolve_occurrence_range`` / ``check_occurrence_range`` in
``testers.tests.test_base`` implement the range semantics shared by every
language tester:

- ``[0, 0]``   -> the item must not occur at all
- ``[n, 0]``   -> at least n, no upper bound (n > 0)
- ``[min, max]`` -> literal inclusive range

Before this, every tester except Octave rewrote ``max == 0`` to infinity,
which silently turned ``[0, 0]`` ("forbidden") into an unconditional pass.

The Python tester's token helpers in ``testers.tests.python.test_class``
count a name as a *sequence* of tokens, so dotted names such as ``np.pi``
are countable at all; per-token comparison could never match them.
"""

from __future__ import annotations

import pytest

from testers.tests.test_base import (  # type: ignore
    check_occurrence_range,
    resolve_occurrence_range,
)
from testers.tests.python.test_class import (  # type: ignore
    _count_single_token,
    _count_token_sequence,
    _tokenize_name,
)


# ---------------------------------------------------------------------------
# resolve_occurrence_range
# ---------------------------------------------------------------------------


class TestResolveOccurrenceRange:
    def test_forbidden_stays_literal(self):
        assert resolve_occurrence_range([0, 0]) == (0, 0)

    def test_min_with_zero_max_is_unbounded(self):
        assert resolve_occurrence_range([5, 0]) == (5, float("inf"))

    def test_literal_range_untouched(self):
        assert resolve_occurrence_range([1, 3]) == (1, 3)


# ---------------------------------------------------------------------------
# check_occurrence_range
# ---------------------------------------------------------------------------


class TestCheckOccurrenceRange:
    def test_forbidden_passes_when_absent(self):
        check_occurrence_range(0, [0, 0], "`eval`")

    def test_forbidden_fails_when_present(self):
        with pytest.raises(pytest.fail.Exception) as exc:
            check_occurrence_range(2, [0, 0], "`eval`")
        assert "must not occur" in str(exc.value)

    def test_unbounded_passes_at_and_above_minimum(self):
        check_occurrence_range(5, [5, 0], "`function`")
        check_occurrence_range(50, [5, 0], "`function`")

    def test_unbounded_fails_below_minimum(self):
        with pytest.raises(pytest.fail.Exception) as exc:
            check_occurrence_range(4, [5, 0], "`function`")
        assert "at least 5" in str(exc.value)

    def test_literal_range_bounds_are_inclusive(self):
        check_occurrence_range(1, [1, 3], "`for`")
        check_occurrence_range(3, [1, 3], "`for`")

    def test_literal_range_fails_outside(self):
        with pytest.raises(pytest.fail.Exception) as exc:
            check_occurrence_range(4, [1, 3], "`for`")
        assert "expected 1-3" in str(exc.value)

    def test_is_style_used_for_document_metrics(self):
        with pytest.raises(pytest.fail.Exception) as exc:
            check_occurrence_range(312, [500, 0], "Word count", style="is")
        assert "Word count is 312" in str(exc.value)
        assert "at least 500" in str(exc.value)


# ---------------------------------------------------------------------------
# _tokenize_name
# ---------------------------------------------------------------------------


class TestTokenizeName:
    def test_single_keyword(self):
        assert _tokenize_name("for") == ["for"]

    def test_dotted_name_splits(self):
        assert _tokenize_name("np.pi") == ["np", ".", "pi"]

    def test_call_expression(self):
        assert _tokenize_name("np.linalg.inv") == ["np", ".", "linalg", ".", "inv"]

    def test_untokenizable_name_returns_none(self):
        assert _tokenize_name("'unterminated") is None


# ---------------------------------------------------------------------------
# token counting
# ---------------------------------------------------------------------------


@pytest.fixture
def write_py(tmp_path):
    def _write(source: str) -> str:
        path = tmp_path / "solution.py"
        path.write_text(source)
        return str(path)
    return _write


class TestCountTokenSequence:
    def test_single_token_name(self, write_py):
        path = write_py("for i in range(3):\n    pass\nfor j in range(2):\n    pass\n")
        assert _count_token_sequence(path, "for") == 2

    def test_dotted_name_counted(self, write_py):
        path = write_py(
            "import numpy as np\n"
            "a = np.pi\n"
            "b = 2 * np.pi\n"
            "c = np.pi / 2\n"
        )
        assert _count_token_sequence(path, "np.pi") == 3

    def test_dotted_name_absent(self, write_py):
        path = write_py("import numpy as np\na = np.e\n")
        assert _count_token_sequence(path, "np.pi") == 0

    def test_comments_do_not_match(self, write_py):
        path = write_py("# np.pi in a comment\na = 1\n")
        assert _count_token_sequence(path, "np.pi") == 0

    def test_strings_do_not_match(self, write_py):
        path = write_py('s = "np.pi"\nt = \'np.pi\'\n')
        assert _count_token_sequence(path, "np.pi") == 0

    def test_sequence_does_not_span_lines(self, write_py):
        # `np` ending one statement and `.pi` starting another must not match.
        path = write_py("np = 1\nx = 2\n")
        assert _count_token_sequence(path, "np.pi") == 0

    def test_matches_are_non_overlapping(self, write_py):
        path = write_py("a = x.x.x.x\n")
        assert _count_token_sequence(path, "x.x") == 2

    def test_untokenizable_name_falls_back_to_exact_token(self, write_py):
        path = write_py("a = 1\n")
        assert _count_token_sequence(path, "'unterminated") == 0


class TestCountSingleToken:
    def test_keyword_in_comment_is_ignored(self, write_py):
        path = write_py("# for loop mentioned here\nx = 1\n")
        assert _count_single_token(path, "for") == 0

    def test_keyword_in_string_is_ignored(self, write_py):
        path = write_py('s = "for"\n')
        assert _count_single_token(path, "for") == 0

    def test_occurance_type_filter(self, write_py):
        path = write_py("for i in range(3):\n    pass\n")
        assert _count_single_token(path, "for", occurance_type="NAME") == 1
        assert _count_single_token(path, "for", occurance_type="OP") == 0
