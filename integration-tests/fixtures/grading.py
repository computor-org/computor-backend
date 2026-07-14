"""Golden-path phase 5: the tutor grades every student × assignment.

`tobi` reviews each submission group and records a grade + status derived from
the test result: a passing run → CORRECTED at 1.0, a failing run →
CORRECTION_NECESSARY at 0.0. The final picture is read back from
`/course-member-gradings` (aggregate) and the student's own view.
"""

from __future__ import annotations

import httpx
import pytest

# GradingStatus (computor_types.grading) — persisted int values.
CORRECTED = 1
CORRECTION_NECESSARY = 2


def grade_for(result_value: float) -> tuple[float, int]:
    """Map a test result (0..1) to a (grade, GradingStatus)."""
    if result_value >= 1.0:
        return 1.0, CORRECTED
    return 0.0, CORRECTION_NECESSARY


@pytest.fixture(scope="session")
def graded_submissions(
    tobi_client: httpx.Client,
    enrolled_students: dict,
    course_contents: dict,
    student_results: dict,
) -> dict:
    """{student: {directory: {grade, status}}} — tobi grades all 18 cells."""
    out: dict = {}
    for student, per_assignment in student_results.items():
        course_member_id = enrolled_students[student]["id"]
        out[student] = {}
        for directory, result in per_assignment.items():
            course_content_id = course_contents["assignments"][directory]["id"]
            value = float(result.get("result") or 0.0)
            grade, status = grade_for(value)
            r = tobi_client.patch(
                f"/tutors/course-members/{course_member_id}/course-contents/{course_content_id}",
                json={"grade": grade, "status": status, "feedback": f"auto (result={value})"},
            )
            assert r.status_code in (200, 201), (
                f"grade {student}/{directory}: {r.status_code} {r.text}"
            )
            out[student][directory] = {"grade": grade, "status": status}
    return out
