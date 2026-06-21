from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path

from fastapi import BackgroundTasks

from computor_backend.analytics import AnalyticsCutoffs, AnalyticsStorageConfig
from computor_backend.analytics.config import ANALYTICS_TABLES
from computor_backend.analytics.service import AnalyticsService
from computor_types.analytics import AnalyticsRefreshRequest


COURSE_ID = "20000000-0000-4000-8000-000000000001"
BOB_MEMBER_ID = "50000000-0000-4000-8000-000000000102"

SUBMISSION_CUTOFF = datetime(2026, 6, 18, 22, 1, tzinfo=timezone.utc)
GRADING_CUTOFF = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)

EXPECTED_ROW_COUNTS = {
    "course": 1,
    "course_member": 5,
    "user": 5,
    "student_profile": 3,
    "course_content_kind": 2,
    "course_content_type": 2,
    "course_content": 3,
    "submission_group": 6,
    "submission_group_member": 6,
    "submission_artifact": 8,
    "submission_grade": 3,
    "result": 3,
}


def main() -> None:
    source_database_url = _require_env("ANALYTICS_SOURCE_DATABASE_URL")
    analytics_root = Path(_require_env("ANALYTICS_ROOT"))
    config = AnalyticsStorageConfig(root=analytics_root, source_name="green")
    service = AnalyticsService(
        config,
        source_database_url=source_database_url,
        export_chunk_size=2,
    )

    request = AnalyticsRefreshRequest(
        source_name="green",
        run_id="system-test",
        submission_cutoff=SUBMISSION_CUTOFF,
        grading_cutoff=GRADING_CUTOFF,
    )
    queued = service.trigger_refresh(
        COURSE_ID,
        request,
        requested_by_user_id="system-test",
        background_tasks=BackgroundTasks(),
    )
    service.run_refresh_job(queued.job_id, request)

    job = service.get_job(queued.job_id)
    _assert_equal("job.status", job.status, "succeeded")
    _assert_equal("job.progress.stage", job.progress.get("stage"), "complete")
    for table, expected in EXPECTED_ROW_COUNTS.items():
        _assert_equal(f"row_counts.{table}", job.row_counts.get(table), expected)

    snapshot_root = config.raw_root / "run=system-test"
    _assert_path(snapshot_root / "manifest.json")
    for table in ANALYTICS_TABLES:
        table_root = snapshot_root / f"table={table}"
        if not list(table_root.glob("*.parquet")):
            raise AssertionError(f"{table_root} has no parquet parts")
    _assert_path(config.duckdb_path)

    cutoffs = AnalyticsCutoffs(
        submission=SUBMISSION_CUTOFF,
        grading=GRADING_CUTOFF,
    ).normalized()
    _assert_course_summary(service, cutoffs)
    _assert_student_list(service, cutoffs)
    _assert_student_timeline(service, cutoffs)
    _assert_student_report(service, cutoffs)

    print("Analytics import system test passed")


def _assert_course_summary(
    service: AnalyticsService,
    cutoffs: AnalyticsCutoffs,
) -> None:
    summary = service.course_summary(COURSE_ID, cutoffs)
    _assert_equal("summary.total_students", summary.total_students, 3)
    _assert_equal("summary.total_max_assignments", summary.total_max_assignments, 6)
    _assert_equal(
        "summary.total_submitted_assignments",
        summary.total_submitted_assignments,
        3,
    )
    _assert_equal("summary.submitted_percentage", summary.submitted_percentage, 50.0)
    _assert_equal("summary.total_graded_assignments", summary.total_graded_assignments, 2)
    _assert_equal("summary.graded_percentage", summary.graded_percentage, 33.33)
    _assert_equal("summary.average_grading", summary.average_grading, 0.2583)
    _assert_equal("summary.latest_job.status", summary.latest_job.status, "succeeded")


def _assert_student_list(
    service: AnalyticsService,
    cutoffs: AnalyticsCutoffs,
) -> None:
    student_list = service.student_list(COURSE_ID, cutoffs)
    _assert_equal("student_list.students", len(student_list.students), 3)
    _assert_equal("student_list.gradings", len(student_list.gradings), 3)

    by_member = {student.course_member_id: student for student in student_list.students}
    bob = by_member[BOB_MEMBER_ID]
    _assert_equal("bob.total_submitted_assignments", bob.total_submitted_assignments, 1)
    _assert_equal("bob.total_graded_assignments", bob.total_graded_assignments, 1)
    _assert_equal("bob.late_submission_count", bob.late_submission_count, 1)


def _assert_student_timeline(
    service: AnalyticsService,
    cutoffs: AnalyticsCutoffs,
) -> None:
    timeline = service.student_timeline(COURSE_ID, BOB_MEMBER_ID, cutoffs)
    _assert_equal("timeline.events", len(timeline.events), 9)
    event_types = {event.event_type for event in timeline.events}
    for event_type in {
        "official_submission",
        "test_submission",
        "test_result",
        "grading",
    }:
        if event_type not in event_types:
            raise AssertionError(f"timeline is missing {event_type}")
    _assert_equal(
        "timeline.last_relation",
        timeline.events[-1].relation_to_submission_cutoff,
        "after_submission_cutoff",
    )


def _assert_student_report(
    service: AnalyticsService,
    cutoffs: AnalyticsCutoffs,
) -> None:
    report = service.student_report(COURSE_ID, BOB_MEMBER_ID, cutoffs)
    _assert_equal(
        "report.checkpoint.total_submitted_assignments",
        report.checkpoint.total_submitted_assignments,
        1,
    )
    _assert_equal(
        "report.grading.total_submitted_assignments",
        report.grading.total_submitted_assignments,
        1,
    )
    _assert_equal("report.timeline.events", len(report.timeline.events), 9)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} must be set")
    return value


def _assert_path(path: Path) -> None:
    if not path.exists():
        raise AssertionError(f"{path} does not exist")


def _assert_equal(name: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise AssertionError(f"{name}: expected {expected!r}, got {actual!r}")


if __name__ == "__main__":
    main()
