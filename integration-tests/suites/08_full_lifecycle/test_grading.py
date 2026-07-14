"""Grading + final state (golden-path phase 5).

`tobi` grades every student × assignment from its test result, then the outcome
is read back three ways: the tutor's submission-group view, the aggregate
`/course-member-gradings`, and each student's own view. The correct student ends
near 100%, the empty near 0%, and the mixed near 50% — the whole lifecycle,
proven end to end.
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = [pytest.mark.lifecycle, pytest.mark.slow]


def test_tutor_can_list_submission_groups(
    tobi_client: httpx.Client, target_course: dict, graded_submissions: dict
) -> None:
    r = tobi_client.get("/tutors/submission-groups", params={"course_id": target_course["id"]})
    assert r.status_code == 200, r.text
    assert len(r.json()) >= 6  # at least the six assignment groups per student


def test_every_cell_graded(graded_submissions: dict) -> None:
    assert set(graded_submissions) == {"s_correct", "s_empty", "s_mixed"}
    for student, per_assignment in graded_submissions.items():
        assert len(per_assignment) == 6, f"{student} not fully graded"


def _gradings_by_member(client: httpx.Client, course_id: str) -> dict:
    r = client.get("/course-member-gradings", params={"course_id": course_id})
    assert r.status_code == 200, r.text
    return {row["course_member_id"]: row for row in r.json()}


def test_final_gradings_reflect_outcomes(
    lena_client: httpx.Client,
    target_course: dict,
    enrolled_students: dict,
    graded_submissions: dict,
) -> None:
    by_member = _gradings_by_member(lena_client, target_course["id"])
    avg = {}
    for student in ("s_correct", "s_empty", "s_mixed"):
        member_id = enrolled_students[student]["id"]
        assert member_id in by_member, f"{student} missing from gradings"
        avg[student] = by_member[member_id]["overall_average_grading"]

    assert avg["s_correct"] == pytest.approx(1.0, abs=0.01), avg
    assert avg["s_empty"] == pytest.approx(0.0, abs=0.01), avg
    assert avg["s_mixed"] == pytest.approx(0.5, abs=0.01), avg
    # And the ordering is strict: correct > mixed > empty.
    assert avg["s_correct"] > avg["s_mixed"] > avg["s_empty"]


def test_record_grading_outcomes(
    student_results: dict, graded_submissions: dict, record_property
) -> None:
    """Emit the per-cell outcomes so reporting renders the grading table."""
    from fixtures.authoring import example_label

    for student, per_assignment in student_results.items():
        for directory, result in per_assignment.items():
            grade = graded_submissions[student][directory]
            record_property(
                "grading_outcome",
                {
                    "student": student,
                    "assignment": example_label(directory),
                    "result": float(result.get("result") or 0.0),
                    "grade": grade["grade"],
                    "status": grade["status"],
                },
            )


def test_student_sees_own_grade(
    student_correct_client: httpx.Client,
    target_course: dict,
    graded_submissions: dict,
) -> None:
    r = student_correct_client.get(
        "/students/course-contents", params={"course_id": target_course["id"]}
    )
    assert r.status_code == 200, r.text
    assignments = [c for c in r.json() if isinstance(c, dict) and c.get("path", "").startswith("unit.")]
    graded = [c for c in assignments if (c.get("submission_group") or {}).get("grading") is not None]
    assert graded, "correct student sees no grades on their assignments"
