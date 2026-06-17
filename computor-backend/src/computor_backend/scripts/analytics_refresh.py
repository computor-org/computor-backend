from __future__ import annotations

from datetime import datetime
import os
import sys

from computor_backend.analytics.service import AnalyticsService
from computor_types.analytics import AnalyticsRefreshRequest


class ImmediateTasks:
    def __init__(self) -> None:
        self.tasks = []

    def add_task(self, func, *args, **kwargs) -> None:
        self.tasks.append((func, args, kwargs))


def main() -> int:
    course_id = _required_env("ANALYTICS_REFRESH_COURSE_ID")
    source_name = os.getenv("ANALYTICS_REFRESH_SOURCE_NAME") or os.getenv(
        "ANALYTICS_SOURCE_NAME",
        "green",
    )
    request = AnalyticsRefreshRequest(
        source_name=source_name,
        submission_cutoff=_datetime_env("ANALYTICS_REFRESH_SUBMISSION_CUTOFF"),
        grading_cutoff=_datetime_env("ANALYTICS_REFRESH_GRADING_CUTOFF"),
        run_id=_optional_env("ANALYTICS_REFRESH_RUN_ID"),
        tables=_tables_env("ANALYTICS_REFRESH_TABLES"),
    )

    tasks = ImmediateTasks()
    service = AnalyticsService.from_settings(source_name=source_name)
    job = service.trigger_refresh(
        course_id=course_id,
        request=request,
        requested_by_user_id=os.getenv("ANALYTICS_REFRESH_REQUESTED_BY_USER_ID")
        or "ops",
        background_tasks=tasks,
    )
    print(f"analytics_job_id={job.job_id}", flush=True)
    if len(tasks.tasks) != 1:
        raise RuntimeError("analytics refresh did not queue exactly one task")

    func, args, kwargs = tasks.tasks[0]
    kwargs = {**kwargs, "progress_callback": _print_progress}
    func(*args, **kwargs)
    job = service.get_job(job.job_id)
    print(f"analytics_status={job.status}", flush=True)
    print(f"analytics_progress={job.progress}", flush=True)
    print(f"analytics_snapshot_path={job.snapshot_path}", flush=True)
    print(f"analytics_row_counts={job.row_counts}", flush=True)
    if job.error:
        print(f"analytics_error={job.error}", flush=True)
    return 0 if job.status == "succeeded" else 1


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    return value if value else None


def _required_env(name: str) -> str:
    value = _optional_env(name)
    if value is None:
        raise RuntimeError(f"{name} is required")
    return value


def _datetime_env(name: str) -> datetime | None:
    value = _optional_env(name)
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _tables_env(name: str) -> list[str] | None:
    value = _optional_env(name)
    if value is None:
        return None
    tables = [part.strip() for part in value.split(",") if part.strip()]
    return tables or None


def _print_progress(job) -> None:
    print(
        f"analytics_job_status={job.status} progress={job.progress}",
        flush=True,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"analytics_refresh_error={exc}", file=sys.stderr, flush=True)
        raise
