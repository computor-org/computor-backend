"""Student workflow (golden-path phase 4).

Students provision repos and submit solutions; the Temporal testing worker runs
each against its assigned example. Correct solutions pass, empty stubs fail, and
the mixed student splits — proving the pipeline discriminates.

Marked slow: this drives real test executions (3 students × 6 assignments),
serialized to respect the 1/s test rate limit.
"""

from __future__ import annotations

import pytest

from fixtures.submissions import MIXED_CORRECT_DIRS, TERMINAL

pytestmark = [pytest.mark.student, pytest.mark.slow]


def _result_value(result: dict) -> float:
    return float(result.get("result") or 0.0)


def test_all_students_provisioned(provisioned_repos: dict) -> None:
    assert set(provisioned_repos) == {"s_correct", "s_empty", "s_mixed"}
    for student, repo in provisioned_repos.items():
        assert repo.get("clone_token"), f"{student}: no one-time clone token"
        assert repo.get("http_url", "").startswith("http://localhost:"), repo.get("http_url")
        assert "forgejo:3030" not in repo.get("http_url", "")


def test_all_results_terminal(student_results: dict) -> None:
    for student, per_assignment in student_results.items():
        assert len(per_assignment) == 6, f"{student} missing results"
        for directory, result in per_assignment.items():
            assert str(result.get("status")).lower() in TERMINAL, (
                f"{student}/{directory}: status {result.get('status')}"
            )


def test_correct_student_passes_all(student_results: dict) -> None:
    for directory, result in student_results["s_correct"].items():
        assert _result_value(result) == 1.0, f"correct/{directory} scored {result.get('result')}"


def test_empty_student_fails_all(student_results: dict) -> None:
    # A broken submission never earns full marks (some example tests award partial
    # credit even for no solution, so assert < 1.0 rather than == 0.0).
    for directory, result in student_results["s_empty"].items():
        assert _result_value(result) < 1.0, f"empty/{directory} scored {result.get('result')}"


def test_mixed_student_splits(student_results: dict) -> None:
    for directory, result in student_results["s_mixed"].items():
        value = _result_value(result)
        if directory in MIXED_CORRECT_DIRS:
            assert value == 1.0, f"mixed/{directory} (correct) scored {value}"
        else:
            assert value < 1.0, f"mixed/{directory} (empty) scored {value}"


def test_correct_beats_empty_per_assignment(student_results: dict) -> None:
    # The pipeline must discriminate: correct >= empty for every assignment.
    for directory in student_results["s_correct"]:
        assert _result_value(student_results["s_correct"][directory]) >= _result_value(
            student_results["s_empty"][directory]
        ), f"{directory}: correct did not beat empty"
