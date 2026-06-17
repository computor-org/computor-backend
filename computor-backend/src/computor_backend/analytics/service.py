from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Callable
from uuid import uuid4

from fastapi import BackgroundTasks
import duckdb

from computor_backend.exceptions import (
    BadRequestException,
    ConfigurationException,
    NotFoundException,
)
from computor_backend.settings import settings
from computor_types.analytics import (
    AnalyticsCourseSummary,
    AnalyticsJobStatus,
    AnalyticsRefreshRequest,
    AnalyticsStudentCheckpoint,
    AnalyticsStudentList,
    AnalyticsStudentReport,
    AnalyticsStudentTimeline,
    AnalyticsTimelineEvent,
)

from .config import ANALYTICS_TABLES, AnalyticsCutoffs, AnalyticsStorageConfig
from .grading_repository import AnalyticsDuckDbGradingRepository
from .job_store import AnalyticsJobStore
from .report_repository import AnalyticsDuckDbReportRepository
from .source import PostgresAnalyticsSource
from .store import AnalyticsDuckDbStore
from ..services.course_member_grading_read import (
    build_course_member_grading_list_response,
    build_course_member_grading_response,
)


class AnalyticsService:
    def __init__(
        self,
        storage_config: AnalyticsStorageConfig,
        source_database_url: str | None = None,
        export_chunk_size: int = 100_000,
    ):
        self.storage_config = storage_config
        self.source_database_url = source_database_url
        self.export_chunk_size = export_chunk_size
        self.job_store = AnalyticsJobStore(storage_config.root)

    @classmethod
    def from_settings(cls, source_name: str | None = None) -> "AnalyticsService":
        return cls(
            AnalyticsStorageConfig(
                root=Path(settings.ANALYTICS_ROOT),
                source_name=source_name or settings.ANALYTICS_SOURCE_NAME,
            ),
            source_database_url=settings.ANALYTICS_SOURCE_DATABASE_URL,
            export_chunk_size=settings.ANALYTICS_EXPORT_CHUNK_SIZE,
        )

    def trigger_refresh(
        self,
        course_id: str,
        request: AnalyticsRefreshRequest,
        requested_by_user_id: str | None,
        background_tasks: BackgroundTasks,
    ) -> AnalyticsJobStatus:
        if not self.source_database_url:
            raise ConfigurationException("Analytics source database is not configured")
        _validate_slug(request.source_name)
        if request.run_id is not None:
            _validate_slug(request.run_id)
        for table in request.tables or ():
            if table not in ANALYTICS_TABLES:
                raise BadRequestException("Unknown analytics source table")

        now = _utc_now()
        job = AnalyticsJobStatus(
            job_id=uuid4().hex,
            course_id=str(course_id),
            source_name=request.source_name,
            requested_by_user_id=requested_by_user_id,
            status="queued",
            progress={"stage": "queued"},
            submission_cutoff=request.submission_cutoff,
            grading_cutoff=request.grading_cutoff,
            created_at=now,
        )
        self.job_store.save(job)
        background_tasks.add_task(self.run_refresh_job, job.job_id, request)
        return job

    def run_refresh_job(
        self,
        job_id: str,
        request: AnalyticsRefreshRequest,
        progress_callback: Callable[[AnalyticsJobStatus], None] | None = None,
    ) -> None:
        job = self._require_job(job_id)
        job.status = "running"
        job.started_at = _utc_now()
        job.progress = {"stage": "exporting"}
        self.job_store.save(job)
        _notify_progress(progress_callback, job)

        source_config = AnalyticsStorageConfig(
            root=self.storage_config.root,
            source_name=request.source_name,
        )
        store = AnalyticsDuckDbStore(source_config.duckdb_path)
        try:
            source = PostgresAnalyticsSource(
                self.source_database_url or "",
                application_name="computor_analytics_blue",
                chunk_size=self.export_chunk_size,
            )

            def save_progress(table: str, state: dict[str, object]) -> None:
                job.progress = {"stage": "exporting", "table": table, **state}
                self.job_store.save(job)
                _notify_progress(progress_callback, job)

            snapshot_path = source.export_snapshot(
                store,
                source_config.raw_root,
                run_id=request.run_id,
                tables=tuple(request.tables or ANALYTICS_TABLES),
                progress=save_progress,
            )
            row_counts, high_water_marks = _read_manifest(snapshot_path)
            job.status = "succeeded"
            job.progress = {"stage": "complete"}
            job.snapshot_path = str(snapshot_path)
            job.row_counts = row_counts
            job.high_water_marks = high_water_marks
            job.finished_at = _utc_now()
            self.job_store.save(job)
            _notify_progress(progress_callback, job)
        except Exception as exc:
            job.status = "failed"
            job.progress = {"stage": "failed"}
            job.error = f"{exc.__class__.__name__}: refresh failed"
            job.finished_at = _utc_now()
            self.job_store.save(job)
            _notify_progress(progress_callback, job)
        finally:
            store.close()

    def get_job(self, job_id: str) -> AnalyticsJobStatus:
        return self._require_job(job_id)

    def list_jobs(self, course_id: str, limit: int = 20) -> list[AnalyticsJobStatus]:
        return self.job_store.list(course_id=str(course_id), limit=limit)

    def course_summary(
        self,
        course_id: str,
        cutoffs: AnalyticsCutoffs,
    ) -> AnalyticsCourseSummary:
        students = self.student_checkpoints(course_id, cutoffs)
        total_students = len(students)
        total_max = sum(student.total_max_assignments for student in students)
        total_submitted = sum(
            student.total_submitted_assignments for student in students
        )
        total_graded = sum(student.total_graded_assignments for student in students)
        grade_sum = sum(
            (student.average_grading or 0) * student.total_graded_assignments
            for student in students
        )
        latest_submission_at = None
        for student in students:
            latest_at = student.latest_submission_at
            if latest_at and (
                latest_submission_at is None or latest_at > latest_submission_at
            ):
                latest_submission_at = latest_at

        return AnalyticsCourseSummary(
            course_id=str(course_id),
            total_students=total_students,
            total_max_assignments=total_max,
            total_submitted_assignments=total_submitted,
            submitted_percentage=_percentage(total_submitted, total_max),
            total_graded_assignments=total_graded,
            graded_percentage=_percentage(total_graded, total_max),
            average_grading=_average(grade_sum, total_graded),
            latest_submission_at=latest_submission_at,
            submission_cutoff=cutoffs.submission,
            grading_cutoff=cutoffs.grading,
            latest_job=self.job_store.latest_for_course(str(course_id)),
        )

    def student_list(
        self,
        course_id: str,
        cutoffs: AnalyticsCutoffs,
    ) -> AnalyticsStudentList:
        connection = self._read_connection()
        try:
            grading_repo = AnalyticsDuckDbGradingRepository(connection, cutoffs)
            return AnalyticsStudentList(
                students=self._student_checkpoints_from_connection(
                    connection,
                    course_id,
                    cutoffs,
                ),
                gradings=build_course_member_grading_list_response(
                    grading_repo,
                    course_id,
                ),
            )
        finally:
            connection.close()

    def student_checkpoints(
        self,
        course_id: str,
        cutoffs: AnalyticsCutoffs,
    ) -> list[AnalyticsStudentCheckpoint]:
        connection = self._read_connection()
        try:
            return self._student_checkpoints_from_connection(
                connection,
                course_id,
                cutoffs,
            )
        finally:
            connection.close()

    def student_report(
        self,
        course_id: str,
        course_member_id: str,
        cutoffs: AnalyticsCutoffs,
    ) -> AnalyticsStudentReport:
        connection = self._read_connection()
        try:
            report_repo = AnalyticsDuckDbReportRepository(connection, cutoffs)
            grading_repo = AnalyticsDuckDbGradingRepository(connection, cutoffs)
            checkpoint_rows = report_repo.get_student_checkpoint_rows(course_id)
            checkpoint = next(
                (
                    _checkpoint_from_row(course_id, row)
                    for row in checkpoint_rows
                    if row["course_member_id"] == str(course_member_id)
                ),
                None,
            )
            if checkpoint is None:
                raise NotFoundException("Analytics course member not found")

            grading = build_course_member_grading_response(
                grading_repo,
                course_member_id,
                course_id,
                checkpoint.model_dump(),
            )
            timeline = AnalyticsStudentTimeline(
                course_id=str(course_id),
                course_member_id=str(course_member_id),
                submission_cutoff=cutoffs.submission,
                grading_cutoff=cutoffs.grading,
                events=[
                    AnalyticsTimelineEvent(**event)
                    for event in report_repo.get_timeline_events(
                        course_id,
                        course_member_id,
                    )
                ],
            )
            return AnalyticsStudentReport(
                checkpoint=checkpoint,
                grading=grading,
                timeline=timeline,
            )
        finally:
            connection.close()

    def student_timeline(
        self,
        course_id: str,
        course_member_id: str,
        cutoffs: AnalyticsCutoffs,
    ) -> AnalyticsStudentTimeline:
        connection = self._read_connection()
        try:
            repo = AnalyticsDuckDbReportRepository(connection, cutoffs)
            return AnalyticsStudentTimeline(
                course_id=str(course_id),
                course_member_id=str(course_member_id),
                submission_cutoff=cutoffs.submission,
                grading_cutoff=cutoffs.grading,
                events=[
                    AnalyticsTimelineEvent(**event)
                    for event in repo.get_timeline_events(course_id, course_member_id)
                ],
            )
        finally:
            connection.close()

    def _student_checkpoints_from_connection(
        self,
        connection: duckdb.DuckDBPyConnection,
        course_id: str,
        cutoffs: AnalyticsCutoffs,
    ) -> list[AnalyticsStudentCheckpoint]:
        repo = AnalyticsDuckDbReportRepository(connection, cutoffs)
        return [
            _checkpoint_from_row(course_id, row)
            for row in repo.get_student_checkpoint_rows(course_id)
        ]

    def _read_connection(self) -> duckdb.DuckDBPyConnection:
        path = self.storage_config.duckdb_path
        if not path.exists():
            raise NotFoundException("Analytics database has not been built")
        return duckdb.connect(str(path), read_only=True)

    def _require_job(self, job_id: str) -> AnalyticsJobStatus:
        job = self.job_store.get(job_id)
        if job is None:
            raise NotFoundException("Analytics job not found")
        return job


def _checkpoint_from_row(
    course_id: str,
    row: dict[str, object],
) -> AnalyticsStudentCheckpoint:
    total_max = int(row["total_max_assignments"] or 0)
    submitted = int(row["total_submitted_assignments"] or 0)
    graded = int(row["total_graded_assignments"] or 0)
    average = row.get("average_grading")
    return AnalyticsStudentCheckpoint(
        course_member_id=str(row["course_member_id"]),
        course_id=str(course_id),
        user_id=str(row["user_id"]) if row.get("user_id") else None,
        username=row.get("username"),
        given_name=row.get("given_name"),
        family_name=row.get("family_name"),
        student_id=row.get("student_id"),
        total_max_assignments=total_max,
        total_submitted_assignments=submitted,
        submitted_percentage=_percentage(submitted, total_max),
        total_graded_assignments=graded,
        graded_percentage=_percentage(graded, total_max),
        average_grading=round(float(average), 4) if average is not None else None,
        latest_submission_at=row.get("latest_submission_at"),
        late_submission_count=int(row.get("late_submission_count") or 0),
    )


def _read_manifest(snapshot_path: Path) -> tuple[dict[str, int], dict[str, dict[str, str]]]:
    manifest_path = snapshot_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row_counts = {}
    high_water_marks = {}
    for table, table_manifest in manifest.get("tables", {}).items():
        row_counts[table] = int(table_manifest.get("rows", 0))
        high_water_marks[table] = table_manifest.get("high_water_marks", {})
    return row_counts, high_water_marks


def _notify_progress(
    callback: Callable[[AnalyticsJobStatus], None] | None,
    job: AnalyticsJobStatus,
) -> None:
    if callback is not None:
        callback(job)


def _validate_slug(value: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.=-]+", value):
        raise BadRequestException("Invalid analytics identifier")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _percentage(value: int, total: int) -> float:
    return round((value / total * 100) if total > 0 else 0.0, 2)


def _average(value: float, count: int) -> float | None:
    return round(value / count, 4) if count > 0 else None
