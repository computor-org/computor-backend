"""``dispatch_submission_test`` — the guard behind #311 / #271.

An official submission (``submit=true``) whose artifact carries no Result is a
dead end: the editor shows a submission with no outcome and nothing ever
grades it. The guard fires the missing test run exactly once and stays silent
in every situation where a run is impossible or already covered.

Rows are created inside a connection-level transaction that is rolled back
after each test, so the dev database is left untouched. Skips when Postgres is
unreachable — same pattern as ``test_grading_access.py``. Temporal is never
contacted: the queue-health probe and the task executor are patched out.
"""

import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.business_logic.testing_orchestration import (
    dispatch_submission_test,
)
from computor_backend.model.artifact import SubmissionArtifact
from computor_backend.model.auth import User
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentType,
    CourseFamily,
    CourseGroup,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.deployment import CourseContentDeployment
from computor_backend.model.example import Example, ExampleRepository, ExampleVersion
from computor_backend.model.organization import Organization
from computor_backend.model.result import Result
from computor_backend.model.service import Service, ServiceType
from computor_types.tasks import TaskStatus, map_task_status_to_int


def _database_url() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres_secret")
    db = os.environ.get("POSTGRES_DB", "computor")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


@pytest.fixture
def db():
    """Session bound to an outer transaction that is always rolled back."""
    try:
        engine = create_engine(_database_url())
        conn = engine.connect()
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Postgres not reachable: {exc}")
    trans = conn.begin()
    session = sessionmaker(bind=conn)()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()


@pytest.fixture
def graph(db):
    """One course with a deployed, testable assignment and a submitted artifact.

    The content's ``testing_service_id`` FK is set (the resolver's fast path),
    so the dispatch does not depend on an executionBackend document.
    """
    suffix = uuid.uuid4().hex[:10]

    student = User(
        given_name="Student", family_name="Test",
        email=f"student.{suffix}@test.local",
    )
    service_user = User(
        given_name="Service", family_name="Account",
        email=f"service.{suffix}@test.local",
    )
    db.add_all([student, service_user])
    db.flush()

    org = Organization(
        title="Dispatch Org",
        organization_type="organization",
        path=Ltree(f"dispatchtest_{suffix}"),
        properties={},
    )
    db.add(org)
    db.flush()

    family = CourseFamily(
        title="Dispatch Family",
        path=Ltree(f"dispatchtest_{suffix}.family"),
        organization_id=org.id,
    )
    db.add(family)
    db.flush()

    course = Course(
        title="Dispatch Course",
        path=Ltree(f"dispatchtest_{suffix}.family.course"),
        course_family_id=family.id,
        organization_id=org.id,
    )
    db.add(course)
    db.flush()

    service_type = ServiceType(
        name="Testing Python",
        path=Ltree(f"testing.dispatch_{suffix}"),
        category="testing",
    )
    db.add(service_type)
    db.flush()

    service = Service(
        slug=f"dispatch-runner-{suffix}",
        name="Dispatch Runner",
        service_type_id=service_type.id,
        user_id=service_user.id,
        config={"language": "python", "temporal": {"task_queue": "testing-python"}},
    )
    db.add(service)
    db.flush()

    content_type = CourseContentType(
        title="Assignment",
        slug=f"assignment-{suffix}",
        course_content_kind_id="assignment",
        course_id=course.id,
    )
    db.add(content_type)
    db.flush()

    content = CourseContent(
        title="A1",
        path=Ltree("a1"),
        course_id=course.id,
        course_content_type_id=content_type.id,
        course_content_kind_id="assignment",
        position=1.0,
        max_group_size=1,
        is_submittable=True,
        testing_service_id=service.id,
    )
    db.add(content)
    db.flush()

    example_repo = ExampleRepository(
        name="Dispatch Repo",
        source_type="minio",
        source_url=f"minio://dispatch-{suffix}",
        organization_id=org.id,
    )
    db.add(example_repo)
    db.flush()

    example = Example(
        example_repository_id=example_repo.id,
        directory="a1",
        identifier=Ltree(f"dispatchtest_{suffix}.a1"),
        title="A1 Example",
    )
    db.add(example)
    db.flush()

    example_version = ExampleVersion(
        example_id=example.id,
        version_tag="v1",
        version_number=1,
        storage_path=f"dispatch-{suffix}/a1/v1",
    )
    db.add(example_version)
    db.flush()

    deployment = CourseContentDeployment(
        course_content_id=content.id,
        example_version_id=example_version.id,
        deployment_status="deployed",
        version_identifier="ref-commit",
    )
    db.add(deployment)
    db.flush()

    course_group = CourseGroup(title="G1", course_id=course.id)
    db.add(course_group)
    db.flush()

    member = CourseMember(
        user_id=student.id,
        course_id=course.id,
        course_role_id="_student",
        course_group_id=course_group.id,
    )
    db.add(member)
    db.flush()

    submission_group = SubmissionGroup(
        max_group_size=1,
        course_id=course.id,
        course_content_id=content.id,
    )
    db.add(submission_group)
    db.flush()

    db.add(
        SubmissionGroupMember(
            course_id=course.id,
            submission_group_id=submission_group.id,
            course_member_id=member.id,
        )
    )

    artifact = SubmissionArtifact(
        submission_group_id=submission_group.id,
        uploaded_by_course_member_id=member.id,
        file_size=1,
        bucket_name="submissions",
        object_key=f"{submission_group.id}/v1",
        version_identifier=f"commit-{suffix}",
        submit=True,
    )
    db.add(artifact)
    db.flush()

    return {
        "artifact": artifact,
        "content": content,
        "member": member,
        "service": service,
        "group": submission_group,
    }


def _patched(executor=None):
    """Patch out Temporal: queue probe passes, workflow submission is recorded."""
    executor = executor or AsyncMock()
    return (
        patch(
            "computor_backend.tasks.queue_health.assert_queue_has_worker",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "computor_backend.tasks.temporal_executor.get_task_executor",
            return_value=executor,
        ),
        executor,
    )


@pytest.mark.asyncio
async def test_submit_without_result_dispatches_the_test(db, graph):
    queue_patch, executor_patch, executor = _patched()
    with queue_patch, executor_patch:
        result = await dispatch_submission_test(graph["artifact"], db)

    assert result is not None
    assert result.submission_artifact_id == graph["artifact"].id
    assert result.status == map_task_status_to_int(TaskStatus.QUEUED)
    assert result.testing_service_id == graph["service"].id
    assert result.version_identifier == graph["artifact"].version_identifier
    executor.submit_task.assert_awaited_once()
    submission = executor.submit_task.await_args.args[0]
    assert submission.queue == "testing-python"
    assert submission.parameters["test_job"]["artifact_id"] == str(graph["artifact"].id)


@pytest.mark.asyncio
async def test_already_tested_artifact_is_left_alone(db, graph):
    queue_patch, executor_patch, executor = _patched()
    with queue_patch, executor_patch:
        first = await dispatch_submission_test(graph["artifact"], db)
        second = await dispatch_submission_test(graph["artifact"], db)

    assert first is not None
    assert second is None
    executor.submit_task.assert_awaited_once()
    count = db.query(Result).filter(
        Result.submission_artifact_id == graph["artifact"].id
    ).count()
    assert count == 1


@pytest.mark.asyncio
async def test_missing_version_identifier_dispatches_nothing(db, graph):
    graph["artifact"].version_identifier = None
    graph["artifact"].properties = None
    db.flush()

    queue_patch, executor_patch, executor = _patched()
    with queue_patch, executor_patch:
        result = await dispatch_submission_test(graph["artifact"], db)

    assert result is None
    executor.submit_task.assert_not_awaited()
    assert db.query(Result).filter(
        Result.submission_artifact_id == graph["artifact"].id
    ).count() == 0


@pytest.mark.asyncio
async def test_missing_deployment_dispatches_nothing(db, graph):
    db.query(CourseContentDeployment).filter(
        CourseContentDeployment.course_content_id == graph["content"].id
    ).delete()
    db.flush()

    queue_patch, executor_patch, executor = _patched()
    with queue_patch, executor_patch:
        result = await dispatch_submission_test(graph["artifact"], db)

    assert result is None
    executor.submit_task.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_workflow_submission_marks_the_result_failed(db, graph):
    executor = AsyncMock()
    executor.submit_task.side_effect = RuntimeError("temporal down")
    queue_patch, executor_patch, _ = _patched(executor)
    with queue_patch, executor_patch:
        result = await dispatch_submission_test(graph["artifact"], db)

    assert result is not None
    assert result.status == map_task_status_to_int(TaskStatus.FAILED)
