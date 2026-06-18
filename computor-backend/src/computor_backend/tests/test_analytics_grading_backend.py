from datetime import datetime, timezone

import duckdb
import pandas as pd
import pytest
from fastapi import BackgroundTasks

from computor_backend.analytics import (
    AnalyticsCutoffs,
    AnalyticsDuckDbGradingRepository,
    AnalyticsDuckDbReportRepository,
    AnalyticsDuckDbStore,
    AnalyticsStorageConfig,
)
from computor_backend.analytics.service import AnalyticsService
from computor_backend.api.analytics import (
    ANALYTICS_READ_ROLE,
    ANALYTICS_REFRESH_ROLE,
    _require_course_role,
)
from computor_backend.exceptions import BadRequestException, ForbiddenException
from computor_backend.permissions.principal import Principal
from computor_types.analytics import AnalyticsRefreshRequest
from computor_backend.services.course_member_grading_read import (
    build_course_member_grading_list_response,
    build_course_member_grading_response,
)


COURSE_ID = "20000000-0000-4000-8000-000000000001"
ALICE_MEMBER_ID = "50000000-0000-4000-8000-000000000101"
BOB_MEMBER_ID = "50000000-0000-4000-8000-000000000102"


def test_duckdb_grading_backend_applies_separate_cutoffs():
    repo = _repo_with_fixture(
        submission_cutoff=datetime(2026, 6, 18, 22, 1, tzinfo=timezone.utc),
        grading_cutoff=datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc),
    )

    rows = build_course_member_grading_list_response(repo, COURSE_ID)
    by_member = {row.course_member_id: row for row in rows}

    alice = by_member[ALICE_MEMBER_ID]
    assert alice.total_max_assignments == 2
    assert alice.total_submitted_assignments == 2
    assert alice.overall_progress_percentage == 100.0
    assert alice.overall_average_grading == 0.425

    bob = by_member[BOB_MEMBER_ID]
    assert bob.total_max_assignments == 2
    assert bob.total_submitted_assignments == 1
    assert bob.overall_progress_percentage == 50.0
    assert bob.overall_average_grading == 0.35


def test_shared_builder_uses_duckdb_backend_for_member_detail():
    repo = _repo_with_fixture(
        submission_cutoff=datetime(2026, 6, 18, 22, 1, tzinfo=timezone.utc),
        grading_cutoff=None,
    )

    result = build_course_member_grading_response(
        repo,
        BOB_MEMBER_ID,
        COURSE_ID,
        {
            "user_id": "10000000-0000-4000-8000-000000000102",
            "username": "bob@example.test",
            "given_name": "Bob",
            "family_name": "Beta",
            "student_id": "m102",
        },
    )

    assert result.total_max_assignments == 2
    assert result.total_submitted_assignments == 1
    assert result.overall_progress_percentage == 50.0

    by_path = {node.path: node for node in result.nodes}
    assert by_path["week1"].max_assignments == 2
    assert by_path["week1"].submitted_assignments == 1
    assert by_path["week1.assignment2"].submissions_count == 0
    assert by_path["week1.assignment2"].test_runs_count == 3
    assert by_path["week1.assignment2"].latest_result_grade == 0.95


def test_duckdb_assignment_details_use_submission_group_limits_without_content_columns():
    conn = duckdb.connect(":memory:")
    _create_schema(conn)
    _insert_fixture(conn)
    conn.execute("ALTER TABLE course_content DROP COLUMN max_test_runs")
    conn.execute("ALTER TABLE course_content DROP COLUMN max_submissions")
    repo = AnalyticsDuckDbGradingRepository(conn)

    result = build_course_member_grading_response(
        repo,
        BOB_MEMBER_ID,
        COURSE_ID,
        {
            "user_id": "10000000-0000-4000-8000-000000000102",
            "username": "bob@example.test",
            "given_name": "Bob",
            "family_name": "Beta",
            "student_id": "m102",
        },
    )

    by_path = {node.path: node for node in result.nodes}
    assert by_path["week1.assignment2"].max_test_runs == 20
    assert by_path["week1.assignment2"].max_submissions == 3


def test_duckdb_store_round_trips_parquet_snapshot(tmp_path):
    store = AnalyticsDuckDbStore(":memory:")
    try:
        frame = pd.DataFrame([
            {"id": "c1", "title": "Course 1"},
            {"id": "c2", "title": "Course 2"},
        ])

        store.replace_table_from_frame("course", frame)
        snapshot_root = tmp_path / "run=unit"
        store.write_table_parquet(
            "course",
            snapshot_root / "table=course" / "part-00000.parquet",
        )
        store.drop_table("course")
        store.load_parquet_snapshot(snapshot_root, tables=("course",))

        rows = store.connection.execute(
            'SELECT id, title FROM "course" ORDER BY id'
        ).fetchall()

        assert rows == [("c1", "Course 1"), ("c2", "Course 2")]
    finally:
        store.close()


def test_report_repository_tracks_actual_grading_checkpoint_counts():
    repo = _report_repo_with_fixture(
        submission_cutoff=datetime(2026, 6, 18, 22, 1, tzinfo=timezone.utc),
        grading_cutoff=datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc),
    )

    rows = repo.get_student_checkpoint_rows(COURSE_ID)
    by_member = {row["course_member_id"]: row for row in rows}

    alice = by_member[ALICE_MEMBER_ID]
    assert alice["total_max_assignments"] == 2
    assert alice["total_submitted_assignments"] == 2
    assert alice["total_graded_assignments"] == 1
    assert alice["average_grading"] == 0.85

    bob = by_member[BOB_MEMBER_ID]
    assert bob["total_max_assignments"] == 2
    assert bob["total_submitted_assignments"] == 1
    assert bob["total_graded_assignments"] == 1
    assert bob["late_submission_count"] == 1
    assert bob["average_grading"] == 0.70


def test_report_repository_counts_score_pass_at_threshold():
    # A pass over a standard example means the latest grade reached 60%, not
    # merely that the student submitted or was graded. Add a graded-but-failing
    # second assignment for Bob so passed (1) differs from graded (2).
    conn = duckdb.connect(":memory:")
    _create_schema(conn)
    _insert_fixture(conn)
    conn.execute(
        "INSERT INTO submission_grade VALUES "
        "('80000000-0000-4000-8000-000000000199', "
        "'70000000-0000-4000-8000-000000000122', "
        "'50000000-0000-4000-8000-000000000002', "
        "'2026-06-25 08:00:00+00', 0.30, 2)"
    )
    repo = AnalyticsDuckDbReportRepository(conn, cutoffs=AnalyticsCutoffs(None, None))
    by_member = {row["course_member_id"]: row for row in repo.get_student_checkpoint_rows(COURSE_ID)}

    alice = by_member[ALICE_MEMBER_ID]
    assert alice["total_graded_assignments"] == 2
    assert alice["standard_passed"] == 2  # 0.85 and 0.90 both clear 60%

    bob = by_member[BOB_MEMBER_ID]
    assert bob["total_graded_assignments"] == 2
    assert bob["standard_passed"] == 1  # 0.70 passes, 0.30 does not


def test_analytics_service_reads_summary_and_timeline_from_duckdb(tmp_path):
    config = AnalyticsStorageConfig(root=tmp_path)
    config.duckdb_path.parent.mkdir(parents=True)
    conn = duckdb.connect(str(config.duckdb_path))
    _create_schema(conn)
    _insert_fixture(conn)
    conn.close()

    service = AnalyticsService(config)
    cutoffs = AnalyticsCutoffs(
        submission=datetime(2026, 6, 18, 22, 1, tzinfo=timezone.utc),
        grading=datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc),
    ).normalized()

    summary = service.course_summary(COURSE_ID, cutoffs)
    assert summary.total_students == 2
    assert summary.total_max_assignments == 4
    assert summary.total_submitted_assignments == 3
    assert summary.submitted_percentage == 75.0
    assert summary.total_graded_assignments == 2
    assert summary.graded_percentage == 50.0
    assert summary.average_grading == 0.775

    timeline = service.student_timeline(COURSE_ID, BOB_MEMBER_ID, cutoffs)
    event_types = [event.event_type for event in timeline.events]
    assert "official_submission" in event_types
    assert "test_submission" in event_types
    assert "test_result" in event_types
    assert "grading" in event_types
    assert timeline.events[-1].relation_to_submission_cutoff == "after_submission_cutoff"


def test_analytics_service_lists_snapshot_courses_by_staff_role(tmp_path):
    service = _service_with_fixture(tmp_path)

    lecturer_courses = service.list_courses(
        user_email="lecturer@example.test",
        minimum_role=ANALYTICS_READ_ROLE,
    )
    tutor_courses = service.list_courses(
        user_email="tutor@example.test",
        minimum_role=ANALYTICS_READ_ROLE,
    )
    student_courses = service.list_courses(
        user_email="alice@example.test",
        minimum_role=ANALYTICS_READ_ROLE,
    )

    assert len(lecturer_courses) == 1
    assert lecturer_courses[0].course_id == COURSE_ID
    assert lecturer_courses[0].title == "Analytics cutoff fixture"
    assert lecturer_courses[0].path == "fixture.course"
    assert lecturer_courses[0].source_name == "green"
    assert lecturer_courses[0].role == "_lecturer"
    assert lecturer_courses[0].total_students == 2
    assert len(tutor_courses) == 1
    assert tutor_courses[0].role == "_tutor"
    assert student_courses == []


def test_analytics_service_checks_snapshot_role_hierarchy(tmp_path):
    service = _service_with_fixture(tmp_path)

    assert service.has_course_role(
        COURSE_ID,
        "tutor@example.test",
        ANALYTICS_READ_ROLE,
    )
    assert not service.has_course_role(
        COURSE_ID,
        "tutor@example.test",
        ANALYTICS_REFRESH_ROLE,
    )
    assert service.has_course_role(
        COURSE_ID,
        "lecturer@example.test",
        ANALYTICS_REFRESH_ROLE,
    )
    assert not service.has_course_role(
        COURSE_ID,
        "alice@example.test",
        ANALYTICS_READ_ROLE,
    )


def test_analytics_service_admin_course_list_includes_all_snapshot_courses(tmp_path):
    service = _service_with_fixture(tmp_path)

    courses = service.list_courses(include_all=True)

    assert len(courses) == 1
    assert courses[0].course_id == COURSE_ID
    assert courses[0].role is None
    assert courses[0].total_students == 2


def test_analytics_access_is_denied_for_default_registered_user(monkeypatch):
    def deny_all(*args):
        return _FakeCoursePermissionQuery(None)

    monkeypatch.setattr("computor_backend.api.analytics.check_course_permissions", deny_all)

    with pytest.raises(ForbiddenException):
        _require_course_role(
            Principal(user_id="10000000-0000-4000-8000-000000000901"),
            object(),
            COURSE_ID,
            ANALYTICS_READ_ROLE,
        )


def test_analytics_access_falls_back_to_snapshot_staff_role(monkeypatch):
    def deny_local_course_role(*args):
        return _FakeCoursePermissionQuery(None)

    class FakeAnalyticsService:
        def has_course_role(self, _course_id, _email, minimum_role):
            return minimum_role == ANALYTICS_READ_ROLE

    monkeypatch.setattr(
        "computor_backend.api.analytics.check_course_permissions",
        deny_local_course_role,
    )
    monkeypatch.setattr(
        "computor_backend.api.analytics._principal_email",
        lambda *_args: "tutor@example.test",
    )
    monkeypatch.setattr(
        "computor_backend.api.analytics.AnalyticsService.from_settings",
        lambda **_kwargs: FakeAnalyticsService(),
    )

    principal = Principal(user_id="10000000-0000-4000-8000-000000000002")
    _require_course_role(principal, object(), COURSE_ID, ANALYTICS_READ_ROLE)
    with pytest.raises(ForbiddenException):
        _require_course_role(principal, object(), COURSE_ID, ANALYTICS_REFRESH_ROLE)


def test_analytics_access_allows_admin_without_course_query(monkeypatch):
    def fail_if_called(*args):
        raise AssertionError("admin should bypass course query")

    monkeypatch.setattr(
        "computor_backend.api.analytics.check_course_permissions",
        fail_if_called,
    )

    _require_course_role(
        Principal(is_admin=True, user_id="10000000-0000-4000-8000-000000000001"),
        object(),
        COURSE_ID,
        ANALYTICS_READ_ROLE,
    )


def test_analytics_access_uses_separate_read_and_refresh_roles(monkeypatch):
    calls = []

    def allow_course_role(_permissions, _entity, course_role_id, _db):
        calls.append(course_role_id)
        return _FakeCoursePermissionQuery(object())

    monkeypatch.setattr(
        "computor_backend.api.analytics.check_course_permissions",
        allow_course_role,
    )

    principal = Principal(user_id="10000000-0000-4000-8000-000000000002")
    _require_course_role(principal, object(), COURSE_ID, ANALYTICS_READ_ROLE)
    _require_course_role(principal, object(), COURSE_ID, ANALYTICS_REFRESH_ROLE)

    assert calls == [ANALYTICS_READ_ROLE, ANALYTICS_REFRESH_ROLE]
    assert ANALYTICS_READ_ROLE == "_tutor"
    assert ANALYTICS_REFRESH_ROLE == "_lecturer"


def test_analytics_rejects_invalid_job_id(tmp_path):
    service = AnalyticsService(AnalyticsStorageConfig(root=tmp_path))

    with pytest.raises(BadRequestException):
        service.get_job("../secret")


def test_analytics_refresh_rejects_unknown_tables(tmp_path):
    service = AnalyticsService(
        AnalyticsStorageConfig(root=tmp_path),
        source_database_url="postgresql+psycopg2://user:pass@example.invalid/db",
    )

    with pytest.raises(BadRequestException):
        service.trigger_refresh(
            course_id=COURSE_ID,
            request=AnalyticsRefreshRequest(tables=["submission_artifact;drop"]),
            requested_by_user_id="10000000-0000-4000-8000-000000000001",
            background_tasks=BackgroundTasks(),
        )


def _repo_with_fixture(
    submission_cutoff: datetime | None,
    grading_cutoff: datetime | None,
) -> AnalyticsDuckDbGradingRepository:
    conn = duckdb.connect(":memory:")
    _create_schema(conn)
    _insert_fixture(conn)
    return AnalyticsDuckDbGradingRepository(
        conn,
        cutoffs=AnalyticsCutoffs(
            submission=submission_cutoff,
            grading=grading_cutoff,
        ),
    )


def _service_with_fixture(tmp_path) -> AnalyticsService:
    config = AnalyticsStorageConfig(root=tmp_path)
    config.duckdb_path.parent.mkdir(parents=True)
    conn = duckdb.connect(str(config.duckdb_path))
    _create_schema(conn)
    _insert_fixture(conn)
    conn.close()
    return AnalyticsService(config)


class _FakeCoursePermissionQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args):
        return self

    def first(self):
        return self.result


def _report_repo_with_fixture(
    submission_cutoff: datetime | None,
    grading_cutoff: datetime | None,
) -> AnalyticsDuckDbReportRepository:
    conn = duckdb.connect(":memory:")
    _create_schema(conn)
    _insert_fixture(conn)
    return AnalyticsDuckDbReportRepository(
        conn,
        cutoffs=AnalyticsCutoffs(
            submission=submission_cutoff,
            grading=grading_cutoff,
        ),
    )


def _create_schema(conn):
    conn.execute("""
    CREATE TABLE "user" (
        id VARCHAR,
        email VARCHAR,
        given_name VARCHAR,
        family_name VARCHAR
    );
    CREATE TABLE student_profile (
        id VARCHAR,
        user_id VARCHAR,
        student_id VARCHAR
    );
    CREATE TABLE course (
        id VARCHAR,
        title VARCHAR,
        path VARCHAR
    );
    CREATE TABLE course_content_kind (
        id VARCHAR,
        submittable BOOLEAN
    );
    CREATE TABLE course_content_type (
        id VARCHAR,
        slug VARCHAR,
        title VARCHAR,
        color VARCHAR,
        course_content_kind_id VARCHAR
    );
    CREATE TABLE course_content (
        id VARCHAR,
        course_id VARCHAR,
        parent_id VARCHAR,
        course_content_type_id VARCHAR,
        course_content_kind_id VARCHAR,
        title VARCHAR,
        path VARCHAR,
        position INTEGER,
        is_submittable BOOLEAN,
        max_test_runs INTEGER,
        max_submissions INTEGER
    );
    CREATE TABLE course_member (
        id VARCHAR,
        course_id VARCHAR,
        user_id VARCHAR,
        course_role_id VARCHAR
    );
    CREATE TABLE submission_group (
        id VARCHAR,
        course_id VARCHAR,
        course_content_id VARCHAR,
        display_name VARCHAR,
        max_group_size INTEGER,
        max_test_runs INTEGER,
        max_submissions INTEGER
    );
    CREATE TABLE submission_group_member (
        id VARCHAR,
        course_id VARCHAR,
        submission_group_id VARCHAR,
        course_member_id VARCHAR
    );
    CREATE TABLE submission_artifact (
        id VARCHAR,
        submission_group_id VARCHAR,
        uploaded_by_course_member_id VARCHAR,
        uploaded_at TIMESTAMPTZ,
        file_size BIGINT,
        bucket_name VARCHAR,
        object_key VARCHAR,
        version_identifier VARCHAR,
        submit BOOLEAN
    );
    CREATE TABLE submission_grade (
        id VARCHAR,
        artifact_id VARCHAR,
        graded_by_course_member_id VARCHAR,
        graded_at TIMESTAMPTZ,
        grade DOUBLE,
        status INTEGER
    );
    CREATE TABLE result (
        id VARCHAR,
        course_member_id VARCHAR,
        submission_artifact_id VARCHAR,
        submission_group_id VARCHAR,
        course_content_id VARCHAR,
        course_content_type_id VARCHAR,
        created_at TIMESTAMPTZ,
        grade DOUBLE,
        status INTEGER,
        version_identifier VARCHAR
    );
    """)


def _insert_fixture(conn):
    conn.execute(f"""
    INSERT INTO "user" VALUES
        ('10000000-0000-4000-8000-000000000001', 'lecturer@example.test', 'Lena', 'Lecturer'),
        ('10000000-0000-4000-8000-000000000002', 'tutor@example.test', 'Tom', 'Tutor'),
        ('10000000-0000-4000-8000-000000000101', 'alice@example.test', 'Alice', 'Alpha'),
        ('10000000-0000-4000-8000-000000000102', 'bob@example.test', 'Bob', 'Beta');
    INSERT INTO student_profile VALUES
        ('11000000-0000-4000-8000-000000000101', '10000000-0000-4000-8000-000000000101', 'm101'),
        ('11000000-0000-4000-8000-000000000102', '10000000-0000-4000-8000-000000000102', 'm102');
    INSERT INTO course VALUES ('{COURSE_ID}', 'Analytics cutoff fixture', 'fixture.course');
    INSERT INTO course_content_kind VALUES ('unit', false), ('assignment', true);
    INSERT INTO course_content_type VALUES
        ('30000000-0000-4000-8000-000000000001', 'mandatory', 'Mandatory', '#2563eb', 'assignment'),
        ('30000000-0000-4000-8000-000000000002', 'unit', 'Unit', '#64748b', 'unit');
    INSERT INTO course_content VALUES
        ('40000000-0000-4000-8000-000000000001', '{COURSE_ID}', NULL, '30000000-0000-4000-8000-000000000002', 'unit', 'Week 1', 'week1', 1, false, NULL, NULL),
        ('40000000-0000-4000-8000-000000000101', '{COURSE_ID}', '40000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', 'assignment', 'Assignment 1', 'week1.assignment1', 1, true, 20, 3),
        ('40000000-0000-4000-8000-000000000102', '{COURSE_ID}', '40000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', 'assignment', 'Assignment 2', 'week1.assignment2', 2, true, 20, 3);
    INSERT INTO course_member VALUES
        ('50000000-0000-4000-8000-000000000001', '{COURSE_ID}', '10000000-0000-4000-8000-000000000001', '_lecturer'),
        ('50000000-0000-4000-8000-000000000002', '{COURSE_ID}', '10000000-0000-4000-8000-000000000002', '_tutor'),
        ('{ALICE_MEMBER_ID}', '{COURSE_ID}', '10000000-0000-4000-8000-000000000101', '_student'),
        ('{BOB_MEMBER_ID}', '{COURSE_ID}', '10000000-0000-4000-8000-000000000102', '_student');
    INSERT INTO submission_group VALUES
        ('60000000-0000-4000-8000-000000000111', '{COURSE_ID}', '40000000-0000-4000-8000-000000000101', 'Alice Assignment 1', 1, 20, 3),
        ('60000000-0000-4000-8000-000000000112', '{COURSE_ID}', '40000000-0000-4000-8000-000000000102', 'Alice Assignment 2', 1, 20, 3),
        ('60000000-0000-4000-8000-000000000121', '{COURSE_ID}', '40000000-0000-4000-8000-000000000101', 'Bob Assignment 1', 1, 20, 3),
        ('60000000-0000-4000-8000-000000000122', '{COURSE_ID}', '40000000-0000-4000-8000-000000000102', 'Bob Assignment 2', 1, 20, 3);
    INSERT INTO submission_group_member VALUES
        ('61000000-0000-4000-8000-000000000111', '{COURSE_ID}', '60000000-0000-4000-8000-000000000111', '{ALICE_MEMBER_ID}'),
        ('61000000-0000-4000-8000-000000000112', '{COURSE_ID}', '60000000-0000-4000-8000-000000000112', '{ALICE_MEMBER_ID}'),
        ('61000000-0000-4000-8000-000000000121', '{COURSE_ID}', '60000000-0000-4000-8000-000000000121', '{BOB_MEMBER_ID}'),
        ('61000000-0000-4000-8000-000000000122', '{COURSE_ID}', '60000000-0000-4000-8000-000000000122', '{BOB_MEMBER_ID}');
    INSERT INTO submission_artifact VALUES
        ('70000000-0000-4000-8000-000000000111', '60000000-0000-4000-8000-000000000111', '{ALICE_MEMBER_ID}', '2026-06-18 20:30:00+00', 1200, 'submissions', 'alice/a1/pre.zip', 'alice-a1-pre', true),
        ('70000000-0000-4000-8000-000000000112', '60000000-0000-4000-8000-000000000112', '{ALICE_MEMBER_ID}', '2026-06-18 21:55:00+00', 1300, 'submissions', 'alice/a2/pre.zip', 'alice-a2-pre', true),
        ('70000000-0000-4000-8000-000000000121', '60000000-0000-4000-8000-000000000121', '{BOB_MEMBER_ID}', '2026-06-17 18:00:00+00', 1100, 'submissions', 'bob/a1/pre.zip', 'bob-a1-pre', true),
        ('70000000-0000-4000-8000-000000000122', '60000000-0000-4000-8000-000000000122', '{BOB_MEMBER_ID}', '2026-06-18 22:20:00+00', 1400, 'submissions', 'bob/a2/late.zip', 'bob-a2-late', true),
        ('70000000-0000-4000-8000-000000000921', '60000000-0000-4000-8000-000000000122', '{BOB_MEMBER_ID}', '2026-06-18 21:30:00+00', 900, 'submissions', 'bob/a2/test1.zip', 'bob-a2-test1', false),
        ('70000000-0000-4000-8000-000000000922', '60000000-0000-4000-8000-000000000122', '{BOB_MEMBER_ID}', '2026-06-18 21:45:00+00', 920, 'submissions', 'bob/a2/test2.zip', 'bob-a2-test2', false),
        ('70000000-0000-4000-8000-000000000923', '60000000-0000-4000-8000-000000000122', '{BOB_MEMBER_ID}', '2026-06-18 21:58:00+00', 940, 'submissions', 'bob/a2/test3.zip', 'bob-a2-test3', false);
    INSERT INTO submission_grade VALUES
        ('80000000-0000-4000-8000-000000000111', '70000000-0000-4000-8000-000000000111', '50000000-0000-4000-8000-000000000002', '2026-06-19 08:00:00+00', 0.85, 1),
        ('80000000-0000-4000-8000-000000000112', '70000000-0000-4000-8000-000000000112', '50000000-0000-4000-8000-000000000002', '2026-06-20 08:00:00+00', 0.90, 1),
        ('80000000-0000-4000-8000-000000000121', '70000000-0000-4000-8000-000000000121', '50000000-0000-4000-8000-000000000002', '2026-06-18 20:00:00+00', 0.70, 3);
    INSERT INTO result VALUES
        ('90000000-0000-4000-8000-000000000921', '{BOB_MEMBER_ID}', '70000000-0000-4000-8000-000000000921', '60000000-0000-4000-8000-000000000122', '40000000-0000-4000-8000-000000000102', '30000000-0000-4000-8000-000000000001', '2026-06-18 21:31:00+00', 0.25, 0, 'bob-a2-test1'),
        ('90000000-0000-4000-8000-000000000922', '{BOB_MEMBER_ID}', '70000000-0000-4000-8000-000000000922', '60000000-0000-4000-8000-000000000122', '40000000-0000-4000-8000-000000000102', '30000000-0000-4000-8000-000000000001', '2026-06-18 21:46:00+00', 0.55, 0, 'bob-a2-test2'),
        ('90000000-0000-4000-8000-000000000923', '{BOB_MEMBER_ID}', '70000000-0000-4000-8000-000000000923', '60000000-0000-4000-8000-000000000122', '40000000-0000-4000-8000-000000000102', '30000000-0000-4000-8000-000000000001', '2026-06-18 21:59:00+00', 0.95, 0, 'bob-a2-test3');
    """)
