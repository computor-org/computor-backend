"""Pure grading-status aggregation, with no DB/service dependencies.

Lives in the util layer (below both repositories and services) so that
``repositories`` can use it without importing *upward* from ``services`` --
which was an inverted dependency. ``services.course_member_grading_stats``
re-exports this for backwards compatibility.
"""
from __future__ import annotations

from typing import Iterable


def aggregate_grading_status(
    statuses: Iterable[str | None],
    default: str | None = "not_reviewed",
) -> str | None:
    valid_statuses = [status for status in statuses if status is not None]
    if not valid_statuses:
        return default
    if "correction_necessary" in valid_statuses:
        return "correction_necessary"
    if "improvement_possible" in valid_statuses:
        return "improvement_possible"
    if all(status == "corrected" for status in valid_statuses):
        return "corrected"
    return "not_reviewed"
