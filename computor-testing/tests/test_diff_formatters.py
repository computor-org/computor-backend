"""Unit tests for the assertion diff formatters in ``testers.tests.test_base``.

These cover the string-only enrichment introduced in #117: helpers that
build the multi-line ``AssertionError`` messages surfaced as
``ComputorReportSub.statusMessage`` for every failing variable test
across all language testers.

The point of the tests is **not** to pin the exact message text (so we
can keep iterating on wording) but to guarantee the salient pieces of
information actually appear:

- variable name in backticks
- both shapes / dtypes when they differ
- a max abs diff number with a coordinate
- mismatching-element samples with actual/expected pairs
- transpose hint when shapes are 2D-reversed
- expected vs. actual scalar values + abs/rel diff
- pattern + actual + a length / first-diff hint for matches/regex/contains
"""

from __future__ import annotations

import numpy as np
import pytest

from testers.tests.test_base import (  # type: ignore
    _clip,
    _first_diff_index,
    _format_array_diff,
    _format_pattern_diff,
    _format_scalar,
    _format_scalar_diff,
    _shape_hint,
    compare_values,
)


# ---------------------------------------------------------------------------
# _format_scalar
# ---------------------------------------------------------------------------


class TestFormatScalar:
    def test_plain_float(self):
        assert _format_scalar(3.14) == "3.14"

    def test_nan(self):
        assert _format_scalar(float("nan")) == "NaN"

    def test_pos_inf(self):
        assert _format_scalar(float("inf")) == "+inf"

    def test_neg_inf(self):
        assert _format_scalar(float("-inf")) == "-inf"

    def test_int(self):
        assert _format_scalar(42) == "42"

    def test_string_uses_repr(self):
        assert _format_scalar("hello") == "'hello'"


# ---------------------------------------------------------------------------
# _shape_hint
# ---------------------------------------------------------------------------


class TestShapeHint:
    def test_same_shape_no_hint(self):
        assert _shape_hint((3, 4), (3, 4)) == ""

    def test_2d_transposed_hint(self):
        hint = _shape_hint((4, 3), (3, 4))
        assert "transpose" in hint.lower()

    def test_higher_rank_reversed_hint(self):
        hint = _shape_hint((2, 3, 4), (4, 3, 2))
        assert "axis order" in hint.lower() or "reversed" in hint.lower()

    def test_same_total_elements_reshape_hint(self):
        hint = _shape_hint((6,), (2, 3))
        assert "reshape" in hint.lower()

    def test_no_relation_no_hint(self):
        # Total element count differs, no transpose pattern.
        assert _shape_hint((2, 2), (3, 3)) == ""


# ---------------------------------------------------------------------------
# _format_array_diff
# ---------------------------------------------------------------------------


class TestFormatArrayDiff:
    def test_includes_name_and_shape(self):
        a = np.array([[1.0, 2.0]])
        e = np.array([[1.0, 3.0]])
        msg = _format_array_diff(a, e, "r2", 1e-9, 1e-12)
        assert "`r2`" in msg
        assert "shape: (1, 2)" in msg

    def test_includes_max_abs_diff_and_index(self):
        a = np.array([1.0, 2.0, 3.0])
        e = np.array([1.0, 2.0, 5.5])
        msg = _format_array_diff(a, e, "x", 1e-9, 1e-12)
        assert "max abs diff" in msg
        # Diff is 2.5 at index 2.
        assert "2.5" in msg
        assert "(2,)" in msg

    def test_includes_mismatch_samples(self):
        a = np.array([1.0, 2.0, 3.0])
        e = np.array([9.0, 2.0, 9.0])
        msg = _format_array_diff(a, e, "x", 1e-9, 1e-12)
        assert "mismatching elements" in msg
        # Both mismatching positions referenced
        assert "actual=1" in msg.replace(" ", "")
        assert "actual=3" in msg.replace(" ", "")
        assert "expected=9" in msg.replace(" ", "")

    def test_caps_mismatch_sample_count(self):
        a = np.zeros(20)
        e = np.arange(1, 21).astype(float)
        msg = _format_array_diff(a, e, "x", 1e-9, 1e-12)
        # Should mention there are more, capped at the configured max.
        assert "more" in msg
        # Should still report total count.
        assert "20" in msg

    def test_dtype_mismatch_shows_both(self):
        a = np.array([1, 2], dtype=np.int32)
        e = np.array([1.0, 2.0], dtype=np.float64)
        msg = _format_array_diff(a, e, "x", None, None)
        assert "int32" in msg
        assert "float64" in msg

    def test_shape_mismatch_skips_index_diff(self):
        # When shapes differ, we cannot report indices — make sure we don't
        # crash and do return *something* useful.
        a = np.array([1.0, 2.0])
        e = np.array([[1.0], [2.0]])
        msg = _format_array_diff(a, e, "x", None, None)
        assert "shape" in msg.lower()
        # No max-abs-diff line because shapes differ.
        assert "max abs diff" not in msg

    def test_nan_disagreement(self):
        a = np.array([1.0, float("nan"), 3.0])
        e = np.array([1.0, 2.0, 3.0])
        msg = _format_array_diff(a, e, "x", None, None)
        assert "NaN" in msg

    def test_non_numeric_arrays(self):
        a = np.array(["a", "b", "c"])
        e = np.array(["a", "x", "c"])
        msg = _format_array_diff(a, e, "labels", None, None)
        assert "unequal elements" in msg
        assert "'b'" in msg
        assert "'x'" in msg


# ---------------------------------------------------------------------------
# _format_scalar_diff
# ---------------------------------------------------------------------------


class TestFormatScalarDiff:
    def test_basic_mismatch(self):
        msg = _format_scalar_diff(3.14, 3.0, "pi", 1e-9, 1e-12)
        assert "`pi`" in msg
        assert "3.14" in msg
        assert "3" in msg  # expected
        assert "abs diff" in msg
        assert "rel diff" in msg

    def test_zero_expected_skips_rel_diff(self):
        msg = _format_scalar_diff(0.5, 0.0, "x", 1e-9, 1e-12)
        # No rel diff line because expected is zero.
        assert "rel diff" not in msg
        assert "abs diff" in msg

    def test_includes_tolerances_when_given(self):
        msg = _format_scalar_diff(1.0, 2.0, "x", 1e-9, 1e-12)
        assert "tolerances" in msg

    def test_no_tolerances_no_line(self):
        msg = _format_scalar_diff(1.0, 2.0, "x", None, None)
        assert "tolerances" not in msg


# ---------------------------------------------------------------------------
# _format_pattern_diff
# ---------------------------------------------------------------------------


class TestFormatPatternDiff:
    def test_includes_pattern_actual_lengths(self):
        msg = _format_pattern_diff("hello world", "hella world", "matches", "out")
        assert "`out`" in msg
        assert "matches" in msg
        assert "hello world" in msg
        assert "hella world" in msg
        assert "lengths" in msg

    def test_matches_shows_first_diff(self):
        # Difference at index 4 ('o' vs 'a').
        msg = _format_pattern_diff("hello", "hella", "matches", "x")
        assert "first diff at index 4" in msg

    def test_clips_long_strings(self):
        long_actual = "a" * 1000
        long_pattern = "b" * 1000
        msg = _format_pattern_diff(long_actual, long_pattern, "matches", "x")
        # Clipped marker present, total length bound is sane.
        assert "more chars" in msg
        assert len(msg) < 2_000


# ---------------------------------------------------------------------------
# _first_diff_index
# ---------------------------------------------------------------------------


class TestFirstDiffIndex:
    def test_equal_strings(self):
        assert _first_diff_index("foo", "foo") is None

    def test_different_at_index_0(self):
        assert _first_diff_index("xfoo", "foo") == 0

    def test_different_in_middle(self):
        assert _first_diff_index("foo", "fxo") == 1

    def test_one_is_prefix(self):
        assert _first_diff_index("foo", "foobar") == 3


# ---------------------------------------------------------------------------
# Integration through compare_values — ensure the message is *raised*
# ---------------------------------------------------------------------------


class TestCompareValuesIntegration:
    def test_array_mismatch_produces_rich_message(self):
        a = np.array([1.0, 2.0, 9.0])
        e = np.array([1.0, 2.0, 3.0])
        with pytest.raises(AssertionError) as exc:
            compare_values(a, e, name="r2")
        msg = str(exc.value)
        assert "`r2`" in msg
        assert "max abs diff" in msg
        # Sanity check: the element pair is referenced.
        assert "actual=9" in msg.replace(" ", "")

    def test_scalar_mismatch_produces_rich_message(self):
        with pytest.raises(AssertionError) as exc:
            compare_values(1.5, 1.0, name="x")
        msg = str(exc.value)
        assert "`x`" in msg
        assert "abs diff" in msg

    def test_shape_mismatch_includes_transpose_hint(self):
        a = np.zeros((4, 3))
        e = np.zeros((3, 4))
        with pytest.raises(AssertionError) as exc:
            compare_values(a, e, name="m")
        msg = str(exc.value)
        assert "wrong shape" in msg
        assert "transpose" in msg.lower()

    def test_dict_key_mismatch_lists_missing_and_extra(self):
        with pytest.raises(AssertionError) as exc:
            compare_values({"a": 1, "x": 2}, {"a": 1, "b": 2}, name="d")
        msg = str(exc.value)
        assert "`d`" in msg
        assert "wrong keys" in msg
        assert "missing" in msg
        assert "'b'" in msg
        assert "extra" in msg
        assert "'x'" in msg

    def test_string_mismatch_includes_first_diff(self):
        with pytest.raises(AssertionError) as exc:
            compare_values("hello", "hella", name="s")
        msg = str(exc.value)
        assert "`s`" in msg
        assert "first diff at index 4" in msg


# ---------------------------------------------------------------------------
# _clip
# ---------------------------------------------------------------------------


class TestClip:
    def test_short_string_unchanged(self):
        assert _clip("hello", max_len=200) == "hello"

    def test_long_string_clipped(self):
        s = "x" * 500
        clipped = _clip(s, max_len=200)
        assert len(clipped) <= 220  # tail "<N more chars>" extra
        assert "more chars" in clipped
