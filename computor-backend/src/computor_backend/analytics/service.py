from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Callable
from uuid import uuid4

from fastapi import BackgroundTasks
import duckdb
import httpx

from computor_backend.exceptions import (
    BadRequestException,
    ConfigurationException,
    NotFoundException,
)
from computor_backend.permissions.principal import course_role_hierarchy
from computor_backend.settings import settings
from computor_types.analytics import (
    AnalyticsCourseAccess,
    AnalyticsCourseSummary,
    AnalyticsExampleSource,
    AnalyticsExampleSourceFile,
    AnalyticsJobStatus,
    AnalyticsRefreshRequest,
    AnalyticsStandardExample,
    AnalyticsStudentCheckpoint,
    AnalyticsStudentList,
    AnalyticsStudentReport,
    AnalyticsStudentTimeline,
    AnalyticsTimelineEvent,
    AnalyticsTutorComment,
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

    def list_courses(
        self,
        *,
        user_email: str | None = None,
        minimum_role: str = "_tutor",
        include_all: bool = False,
    ) -> list[AnalyticsCourseAccess]:
        connection = self._read_connection()
        try:
            repo = AnalyticsDuckDbReportRepository(connection)
            if include_all:
                rows = repo.get_course_rows()
            elif user_email:
                rows = [
                    row
                    for row in repo.get_course_rows_for_user_email(user_email)
                    if _role_allows(str(row.get("role")), minimum_role)
                ]
            else:
                rows = []
            return self._course_access_from_rows(rows, include_role=not include_all)
        finally:
            connection.close()

    def has_course_role(
        self,
        course_id: str,
        user_email: str | None,
        minimum_role: str,
    ) -> bool:
        if not user_email:
            return False
        connection = self._read_connection()
        try:
            repo = AnalyticsDuckDbReportRepository(connection)
            roles = repo.get_course_roles_for_user_email(course_id, user_email)
            return any(_role_allows(role, minimum_role) for role in roles)
        finally:
            connection.close()

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
            (student.average_score or 0) * student.total_graded_assignments
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

    def student_examples(
        self,
        course_id: str,
        course_member_id: str,
        cutoffs: AnalyticsCutoffs,
    ) -> list[AnalyticsStandardExample]:
        connection = self._read_connection()
        try:
            repo = AnalyticsDuckDbReportRepository(connection, cutoffs)
            return _examples_from_rows(
                repo.get_student_examples(course_id, course_member_id)
            )
        finally:
            connection.close()

    def example_source(
        self,
        course_id: str,
        content_id: str,
    ) -> AnalyticsExampleSource | None:
        """Source files of the example deployed to a content, fetched live from
        the source instance's API server side, so the browser never touches the
        source. Resolves the content's deployed example version, then downloads
        its files. None (a calm 'not available' notice) when the source API is
        unconfigured/unreachable or the content has no deployment."""
        base = settings.ANALYTICS_SOURCE_API_URL
        token = settings.ANALYTICS_SOURCE_API_TOKEN
        if not base or not token:
            return None
        base = base.rstrip("/")

        content = _source_get_json(base, token, f"course-contents/{content_id}")
        deployment = (content or {}).get("deployment") or {}
        version_id = deployment.get("example_version_id")
        if not version_id:
            return None

        payload = _source_get_json(base, token, f"examples/download/{version_id}")
        if payload is None:
            return None
        title = (
            deployment.get("example_identifier")
            or (payload.get("identifier") if isinstance(payload, dict) else None)
            or "Example source"
        )
        return AnalyticsExampleSource(
            content_id=str(content_id),
            title=str(title),
            files=_source_files_from_payload(payload),
        )

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

    def _course_access_from_rows(
        self,
        rows: list[dict[str, object]],
        *,
        include_role: bool,
    ) -> list[AnalyticsCourseAccess]:
        courses: dict[str, AnalyticsCourseAccess] = {}
        for row in rows:
            course_id = str(row["course_id"])
            role = str(row["role"]) if include_role and row.get("role") else None
            current = courses.get(course_id)
            if current and (
                current.role is None
                or role is None
                or course_role_hierarchy.get_role_level(current.role)
                >= course_role_hierarchy.get_role_level(role)
            ):
                continue
            courses[course_id] = AnalyticsCourseAccess(
                course_id=course_id,
                title=row.get("title"),
                path=row.get("path"),
                source_name=self.storage_config.source_name,
                role=role,
                total_students=int(row.get("total_students") or 0),
                latest_job=self.job_store.latest_for_course(course_id),
            )
        return list(courses.values())

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
    passed = int(row.get("standard_passed") or 0)
    average = row.get("average_grading")
    average_value = round(float(average), 4) if average is not None else None
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
        average_grading=average_value,
        latest_submission_at=row.get("latest_submission_at"),
        late_submission_count=int(row.get("late_submission_count") or 0),
        standard_total=total_max,
        standard_passed=passed,
        pass_rate=_percentage(passed, total_max),
        average_score=average_value,
    )


# Score-pass and integrity heuristics. Deliberately simple: derivable from the
# already-ingested snapshot with no extra requests or statistics.
_PASS_THRESHOLD = 0.6
_LOW_ITERATION_MAX_ROUNDS = 1
# Burst = a steep stretch of the submission curve: this many consecutive
# official submissions (capped at how many the student has) completed within the
# span below. Measuring the gradient over many examples avoids flagging steady
# one-per-week work.
_BURST_WINDOW_EXAMPLES = 15
_BURST_MIN_WINDOW = 3
_BURST_MAX_SPAN_SECONDS = 7 * 24 * 3600
_GRADING_STATUS_CORRECTION_NECESSARY = 2


def _examples_from_rows(rows: list[dict[str, Any]]) -> list[AnalyticsStandardExample]:
    examples: list[AnalyticsStandardExample] = []
    for row in rows:
        grade = row.get("grade")
        score = float(grade) if grade is not None else None
        passed = score is not None and score >= _PASS_THRESHOLD
        submitted_at = row.get("submitted_at")
        official = submitted_at is not None
        test_rounds = int(row.get("test_rounds") or 0)
        status = int(row.get("grade_status") or 0)
        comment_text = row.get("comment")

        comments: list[AnalyticsTutorComment] = []
        if comment_text:
            comments.append(
                AnalyticsTutorComment(
                    author_role="tutor",
                    text=str(comment_text),
                    created_at=row.get("graded_at"),
                )
            )

        flags: list[str] = []
        if passed and test_rounds <= _LOW_ITERATION_MAX_ROUNDS:
            flags.append("low_iteration")
        if comment_text and status == _GRADING_STATUS_CORRECTION_NECESSARY:
            flags.append("tutor_concern")

        examples.append(
            AnalyticsStandardExample(
                content_id=str(row["content_id"]),
                path=str(row["path"]),
                title=row.get("title") or str(row["path"]),
                category=row.get("category"),
                score=score,
                passed=passed,
                test_rounds=test_rounds,
                submitted_at=submitted_at,
                official=official,
                late=bool(row.get("late")),
                flags=flags,
                comments=comments,
            )
        )
    _tag_velocity(examples)
    return examples


def _tag_velocity(examples: list[AnalyticsStandardExample]) -> None:
    """Flag a submission burst by the steepness of the submission curve, not by a
    count of threshold crossings. Take a window of consecutive official
    submissions (a gradient over many examples) and flag the single steepest one
    when those examples were completed within a short span. Steady weekly work
    spreads the window over weeks and never triggers; one busy late week does."""
    official = sorted(
        (ex for ex in examples if ex.official and ex.submitted_at is not None),
        key=lambda ex: ex.submitted_at,
    )
    n = len(official)
    window = min(_BURST_WINDOW_EXAMPLES, n)
    if window < _BURST_MIN_WINDOW:
        return
    best_span: float | None = None
    best_start = 0
    for start in range(0, n - window + 1):
        span = (
            official[start + window - 1].submitted_at - official[start].submitted_at
        ).total_seconds()
        if best_span is None or span < best_span:
            best_span = span
            best_start = start
    if best_span is not None and best_span <= _BURST_MAX_SPAN_SECONDS:
        for ex in official[best_start : best_start + window]:
            if "velocity" not in ex.flags:
                ex.flags.append("velocity")


def _source_get_json(base: str, token: str, path: str) -> object | None:
    """GET a JSON resource from the source instance API with the read-only
    service token. None on any error, so the source view degrades quietly."""
    try:
        response = httpx.get(
            f"{base}/{path}",
            headers={"X-API-Token": token},
            timeout=20.0,
        )
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def _source_files_from_payload(payload: object) -> list[AnalyticsExampleSourceFile]:
    """Map an ExampleDownloadResponse `files` map to readable source. Plain text
    passes through; data-URI files are decoded and kept when they are UTF-8 text
    (e.g. notebooks, which the download wraps as base64 octet-stream); genuine
    binaries (images) are skipped. Notebooks render as their cell sources."""
    files = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(files, dict):
        return []
    result: list[AnalyticsExampleSourceFile] = []
    for name, content in sorted(files.items()):
        if not isinstance(content, str):
            continue
        text = _decode_source_text(content) if content.startswith("data:") else content
        if text is None:
            continue
        if str(name).endswith(".ipynb"):
            text = _notebook_to_source(text)
        result.append(AnalyticsExampleSourceFile(name=str(name), content=text))
    return result


def _decode_source_text(data_uri: str) -> str | None:
    """Decode a data: URI to UTF-8 text, or None when it is binary."""
    import base64
    from urllib.parse import unquote_to_bytes

    try:
        header, _, data = data_uri.partition(",")
        raw = base64.b64decode(data) if ";base64" in header else unquote_to_bytes(data)
        return raw.decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def _notebook_to_source(text: str) -> str:
    """Flatten a Jupyter notebook to its code and markdown cells, so the source
    view shows the actual code rather than raw notebook JSON."""
    try:
        notebook = json.loads(text)
    except ValueError:
        return text
    cells = notebook.get("cells") if isinstance(notebook, dict) else None
    if not isinstance(cells, list):
        return text
    blocks: list[str] = []
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        source = cell.get("source", "")
        body = "".join(source) if isinstance(source, list) else str(source)
        if not body.strip():
            continue
        if cell.get("cell_type") == "markdown":
            body = "\n".join(f"# {line}" for line in body.splitlines())
        blocks.append(body)
    return "\n\n".join(blocks) if blocks else text


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


def _role_allows(role: str | None, minimum_role: str) -> bool:
    if not role:
        return False
    return course_role_hierarchy.has_role_permission(role, minimum_role)
