"""``Course.submission_feedback`` decides who grades an official submission."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import Boolean, DateTime, Float, Integer, create_engine, event, text
from sqlalchemy.orm import Session

from computor_backend.business_logic import submissions
from computor_backend.exceptions import ForbiddenException
from computor_backend.model import Base
from computor_backend.model.artifact import SubmissionGrade
from computor_backend.permissions.principal import Principal
from computor_backend.repositories.course_content_subqueries import (
    latest_submission_grade_status_subquery,
)
from computor_types.courses import CourseUpdate
from computor_types.grading import GradingStatus
from computor_types.tasks import ResultStatus


def uid(number):
    return str(UUID(int=number))


STUDENT, TUTOR = uid(1), uid(2)
COURSE, GROUP, ARTIFACT, MEMBER, TUTOR_MEMBER = [uid(i) for i in range(11, 16)]


def _column_type(column):
    if isinstance(column.type, (Boolean, Integer)):
        return "INTEGER"
    if isinstance(column.type, Float):
        return "REAL"
    return "TEXT"


@pytest.fixture
def db(monkeypatch):
    # Only the columns, without PostgreSQL DDL; timestamps get SQLite defaults
    # in place of the server defaults the ORM leaves to the database.
    monkeypatch.setattr(submissions, "register_post_commit", lambda db, callback: None)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for name in [
            "user", "course", "course_member", "submission_group",
            "submission_group_member", "submission_artifact", "submission_grade", "result",
            "result_artifact",
        ]:
            table = Base.metadata.tables[name]
            columns = []
            for c in table.columns:
                column = f'"{c.name}" {_column_type(c)}'
                if isinstance(c.type, DateTime):
                    column += " DEFAULT CURRENT_TIMESTAMP"
                columns.append(column)
            connection.execute(text(f'CREATE TABLE "{table.name}" ({", ".join(columns)})'))
        connection.execute(text("INSERT INTO \"user\" (id) VALUES (:s), (:t)"), {"s": STUDENT, "t": TUTOR})
        connection.execute(
            text("INSERT INTO course (id, submission_feedback) VALUES (:id, 'tests')"), {"id": COURSE}
        )
        connection.execute(
            text(
                "INSERT INTO course_member (id, user_id, course_id, course_role_id) "
                "VALUES (:m, :s, :c, '_student'), (:t, :tu, :c, '_tutor')"
            ),
            {"m": MEMBER, "s": STUDENT, "t": TUTOR_MEMBER, "tu": TUTOR, "c": COURSE},
        )
        connection.execute(
            text("INSERT INTO submission_group (id, course_id, course_content_id) VALUES (:g, :c, :c)"),
            {"g": GROUP, "c": COURSE},
        )
        connection.execute(
            text("INSERT INTO submission_group_member (id, submission_group_id, course_member_id) VALUES (:i, :g, :m)"),
            {"i": uid(30), "g": GROUP, "m": MEMBER},
        )
        connection.execute(
            text("INSERT INTO submission_artifact (id, submission_group_id, submit) VALUES (:a, :g, 1)"),
            {"a": ARTIFACT, "g": GROUP},
        )
    # SQLite returns no server-generated key, so the ORM needs one up front.
    def assign_id(mapper, connection, target):
        target.id = target.id or str(uuid4())

    event.listen(SubmissionGrade, "before_insert", assign_id)
    with Session(engine) as session:
        yield session
    event.remove(SubmissionGrade, "before_insert", assign_id)
    engine.dispose()


def add_result(db, status=ResultStatus.FINISHED, value=0.75):
    db.execute(
        text(
            "INSERT INTO result (id, submission_artifact_id, submission_group_id, course_member_id,"
            " course_content_id, course_content_type_id, version_identifier, status, result) "
            "VALUES (:id, :a, :g, :m, :c, :c, 'v1', :s, :v)"
        ),
        {"id": uid(40), "a": ARTIFACT, "g": GROUP, "m": MEMBER, "c": COURSE, "s": int(status), "v": value},
    )


def set_feedback(db, value):
    db.execute(text("UPDATE course SET submission_feedback = :v"), {"v": value})


def grades(db):
    return db.query(SubmissionGrade).all()


def unreviewed(db):
    sub = latest_submission_grade_status_subquery(None, None, None, db)
    return db.query(sub.c.is_unreviewed).filter(sub.c.submission_group_id == GROUP).scalar()


@pytest.mark.parametrize("feedback", ["tests", "tests_and_lena"])
def test_finished_tests_grade_the_submission_and_leave_the_review_queue(db, feedback):
    set_feedback(db, feedback)
    add_result(db)
    assert unreviewed(db) == 1

    submissions.grade_from_official_tests(ARTIFACT, db)

    [grade] = grades(db)
    assert grade.grade == 0.75
    assert grade.status == int(GradingStatus.CORRECTED)
    assert grade.graded_by_course_member_id is None
    assert unreviewed(db) == 0


def test_human_courses_wait_for_a_tutor(db):
    set_feedback(db, "human")
    add_result(db)
    submissions.grade_from_official_tests(ARTIFACT, db)
    assert grades(db) == []


@pytest.mark.parametrize("status", [ResultStatus.RUNNING, ResultStatus.FAILED, ResultStatus.CRASHED])
def test_only_a_finished_run_counts(db, status):
    add_result(db, status=status)
    submissions.grade_from_official_tests(ARTIFACT, db)
    assert grades(db) == []


def test_a_practice_run_is_graded_once_it_is_submitted(db):
    db.execute(text("UPDATE submission_artifact SET submit = 0"))
    add_result(db)
    submissions.grade_from_official_tests(ARTIFACT, db)
    assert grades(db) == []

    db.execute(text("UPDATE submission_artifact SET submit = 1"))
    db.expire_all()
    submissions.grade_from_official_tests(ARTIFACT, db)
    assert len(grades(db)) == 1


def test_existing_grades_are_kept_and_repeat_calls_add_nothing(db):
    add_result(db)
    db.add(SubmissionGrade(artifact_id=ARTIFACT, graded_by_course_member_id=TUTOR_MEMBER,
                           grade=1.0, status=int(GradingStatus.CORRECTED)))
    db.flush()
    submissions.grade_from_official_tests(ARTIFACT, db)
    submissions.grade_from_official_tests(ARTIFACT, db)
    [grade] = grades(db)
    assert grade.graded_by_course_member_id == TUTOR_MEMBER


def test_nobody_can_edit_a_grade_as_if_they_had_given_it(db):
    add_result(db)
    grade = submissions.grade_from_official_tests(ARTIFACT, db)
    with pytest.raises(ForbiddenException):
        submissions.update_grade(grade.id, 1.0, None, None, Principal(user_id=STUDENT), db)


def test_course_update_accepts_only_the_three_modes():
    assert CourseUpdate(submission_feedback="tests").submission_feedback == "tests"
    assert "submission_feedback" not in CourseUpdate().model_dump(exclude_unset=True)
    with pytest.raises(ValidationError):
        CourseUpdate(submission_feedback="lena")



@pytest.mark.asyncio
async def test_the_worker_reporting_a_finished_run_grades_the_submission(db, monkeypatch):
    from computor_backend.api import results as results_api
    from computor_backend.services import result_storage
    from computor_types.results import ResultUpdate
    from computor_types.tasks import TaskStatus

    async def no_result_json(result_id):
        return None

    monkeypatch.setattr(result_storage, "retrieve_result_json", no_result_json)
    monkeypatch.setattr(results_api, "announce_submission_group_updated", lambda *a, **k: None)
    add_result(db, status=ResultStatus.RUNNING, value=None)

    await results_api.update_result(
        uid(40), ResultUpdate(status=TaskStatus.FINISHED, result=0.5),
        Principal(user_id=TUTOR, is_admin=True), db, cache=None,
    )
    [grade] = grades(db)
    assert grade.grade == 0.5
