"""Skipped tests must not reduce the grade (#232).

Legitimate skips (test types not implemented for a language, unsupported
qualifications) are not the student's doing, so ``compute_result_value``
excludes them from the denominator. An all-skipped run must not become 100%.
"""

import pytest

from computor_backend.tasks.temporal_base import (
    compute_result_value,
    extract_test_counts,
)


def _results(passed, failed, total, skipped):
    return {
        "summary": {
            "passed": passed,
            "failed": failed,
            "total": total,
            "skipped": skipped,
        }
    }


def test_counts_include_skipped():
    assert extract_test_counts(_results(3, 0, 4, 1)) == (3, 0, 4, 1)


def test_counts_from_flat_results():
    flat = {"passed": 2, "failed": 1, "total": 3}
    assert extract_test_counts(flat) == (2, 1, 3, 0)


def test_one_skip_out_of_four_is_full_marks():
    assert compute_result_value(_results(3, 0, 4, 1)) == pytest.approx(1.0)


def test_skip_no_longer_taxes_a_failed_run():
    assert compute_result_value(_results(2, 1, 4, 1)) == pytest.approx(2 / 3)


def test_all_skipped_is_inconclusive_not_a_pass():
    assert compute_result_value(_results(0, 0, 4, 4)) == 0.0


def test_no_skips_unchanged():
    assert compute_result_value(_results(3, 1, 4, 0)) == pytest.approx(0.75)


def test_empty_run_is_zero():
    assert compute_result_value(_results(0, 0, 0, 0)) == 0.0
