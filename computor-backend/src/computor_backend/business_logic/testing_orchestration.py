"""Shared orchestration rules for student and tutor test runs.

``create_test_run`` (api/tests.py), ``create_tutor_test`` (api/tutor.py) and
``business_logic.submissions.create_test_result`` each re-implemented parts
of "which artifact, is a test already running, which task queue is valid".
These helpers are the single home for those rules.

Note the two call sites deliberately differ in how a blocking test is
handled (idempotent return vs hard 400) — that policy stays with the
caller; only the queries and validation live here.
"""
import json
import logging
import re
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from computor_backend.business_logic.content_visibility import enforce_content_visible
from computor_backend.business_logic.submission_limits import enforce_max_test_runs
from computor_backend.exceptions import BadRequestException, NotFoundException
from computor_backend.model.artifact import SubmissionArtifact
from computor_backend.model.result import Result
from computor_types.tasks import (
    RETRYABLE_RESULT_STATUSES,
    ResultStatus,
    TaskStatus,
    map_task_status_to_int,
)

logger = logging.getLogger(__name__)

# A member's earlier test only stops a re-run while it is not in one of these
# states (a crashed/cancelled/failed run may always be retried). Defined once in
# computor_types.tasks, which the partial unique indexes on ``result`` are also
# built from — these must not drift apart.
RETRYABLE_STATUSES = RETRYABLE_RESULT_STATUSES

IN_PROGRESS_STATUSES = (
    int(ResultStatus.SCHEDULED),
    int(ResultStatus.PENDING),
    int(ResultStatus.RUNNING),
    int(ResultStatus.PAUSED),
)


def resolve_artifact_for_test(test_create, db: Session) -> SubmissionArtifact:
    """Resolve which artifact to test from a ``TestCreate`` payload.

    Three modes: direct ``artifact_id``, ``submission_group_id`` +
    ``version_identifier``, or ``submission_group_id`` only (latest upload).
    """
    if test_create.artifact_id:
        artifact = db.query(SubmissionArtifact).filter(
            SubmissionArtifact.id == test_create.artifact_id
        ).first()

        if not artifact:
            raise NotFoundException(
                error_code="SUBMIT_001",
                detail="Submission artifact not found"
            )
        return artifact

    if test_create.submission_group_id:
        if test_create.version_identifier:
            artifact = db.query(SubmissionArtifact).filter(
                SubmissionArtifact.submission_group_id == test_create.submission_group_id,
                SubmissionArtifact.version_identifier == test_create.version_identifier
            ).order_by(SubmissionArtifact.created_at.desc()).first()

            if not artifact:
                raise NotFoundException(
                    error_code="SUBMIT_001",
                    detail=f"No artifact found for submission group {test_create.submission_group_id} "
                           f"with version {test_create.version_identifier}"
                )
            return artifact

        artifact = db.query(SubmissionArtifact).filter(
            SubmissionArtifact.submission_group_id == test_create.submission_group_id
        ).order_by(SubmissionArtifact.created_at.desc()).first()

        if not artifact:
            raise NotFoundException(
                error_code="SUBMIT_001",
                detail=f"No artifacts found for submission group {test_create.submission_group_id}. "
                       f"Student must submit first."
            )
        return artifact

    raise BadRequestException(
        error_code="SUBMIT_007",
        detail="Must provide either artifact_id or submission_group_id to identify what to test"
    )


def find_active_test(
    artifact_id: UUID | str,
    course_member_id: UUID | str,
    db: Session,
) -> Optional[Result]:
    """Return this member's non-retryable (running or finished) test, if any."""
    return db.query(Result).filter(
        and_(
            Result.submission_artifact_id == artifact_id,
            Result.course_member_id == course_member_id,
            ~Result.status.in_(RETRYABLE_STATUSES)
        )
    ).first()


def enforce_test_limits(
    artifact: SubmissionArtifact,
    course_member_id: UUID | str,
    submission_group,
    course_content,
    db: Session,
    *,
    exempt: bool = False,
) -> None:
    """Hard-fail variant of the test-limitation rules.

    Used where an existing active test is always an error (test-result
    ingestion); ``create_test_run`` instead syncs the old run against
    Temporal and may return it idempotently.

    The budget itself lives in ``business_logic.submission_limits`` so that
    enforcement and the counts shown to students cannot drift apart.
    """
    if find_active_test(artifact.id, course_member_id, db):
        raise BadRequestException(
            detail="You have already run a test on this artifact. "
                   "Multiple tests are not allowed unless the previous test crashed or was cancelled."
        )

    # Content hidden from students accepts no ingested results from them
    # either (issue #338); staff are exempt on the same terms as the budget.
    enforce_content_visible(db, course_content, exempt=exempt)

    enforce_max_test_runs(db, submission_group, course_content, exempt=exempt)


async def sync_result_status_from_temporal(
    result: Result,
    db: Session,
    *,
    treat_missing_as_crashed: bool = False,
    sync_in_progress: bool = False,
) -> bool:
    """Reconcile a Result row against its Temporal workflow.

    Returns True while the workflow is still running (QUEUED/STARTED).
    ``treat_missing_as_crashed`` marks the row CRASHED when the workflow
    cannot be found; ``sync_in_progress`` also persists in-progress status
    transitions (status-poll endpoints) instead of only terminal ones.
    """
    from computor_backend.tasks import get_task_executor
    from computor_backend.tasks.temporal_executor import TaskNotFoundError

    if not result.test_system_id:
        return False

    task_executor = get_task_executor()
    try:
        task_info = await task_executor.get_task_status(result.test_system_id)
    except TaskNotFoundError as e:
        if treat_missing_as_crashed:
            logger.warning(
                f"Temporal workflow {result.test_system_id} not found, "
                f"marking Result {result.id} as CRASHED: {e}"
            )
            result.status = int(ResultStatus.CRASHED)
            db.commit()
        else:
            logger.warning(f"Could not check Temporal status: {e}")
        return False
    except Exception as e:
        # Temporal is unreachable, not the workflow missing. Report "still
        # running" so a live run is never declared dead (and never duplicated)
        # just because we briefly could not ask.
        logger.warning(
            f"Temporal unreachable while syncing Result {result.id}; "
            f"leaving status unchanged: {e}"
        )
        return result.status in IN_PROGRESS_STATUSES

    if task_info.status in (TaskStatus.QUEUED, TaskStatus.STARTED):
        if sync_in_progress:
            new_status = map_task_status_to_int(task_info.status)
            if new_status != result.status:
                result.status = new_status
                db.commit()
        return True

    # Terminal state - sync the row when it drifted from Temporal reality
    if sync_in_progress:
        new_status = map_task_status_to_int(task_info.status)
    else:
        terminal_map = {
            TaskStatus.FINISHED: int(ResultStatus.FINISHED),
            TaskStatus.FAILED: int(ResultStatus.FAILED),
            TaskStatus.CANCELLED: int(ResultStatus.CANCELLED),
        }
        new_status = terminal_map.get(task_info.status, int(ResultStatus.CRASHED))

    if new_status != result.status:
        logger.info(
            f"Status synced from Temporal for Result {result.id}: "
            f"{task_info.status} -> status {new_status}"
        )
        result.status = new_status
        db.commit()
    return False


# A service that does not name a queue is routed to the fleet for its language.
# One worker image per language is the intended topology, so the queue is a
# function of the language rather than a third value to keep in sync by hand.
TASK_QUEUE_PREFIX = "testing"


def _queue_token(value: str) -> str:
    """Normalise one component of a derived queue name.

    Lowercase; anything outside ``[a-z0-9.]`` collapses to a single dash, so
    ``R2025b`` → ``r2025b`` and ``3.13`` stays ``3.13``.
    """
    slug = re.sub(r"[^a-z0-9.]+", "-", value.strip().lower())
    return slug.strip("-")


def default_task_queue_for_language(
    language: str, language_version: Optional[str] = None
) -> str:
    """The conventional queue for a runner: ``testing-<language>[-<version>]``.

    The queue names the *runner*, and a runner is identified by language AND
    version — two workers with different Python versions are not
    interchangeable. Keying the queue on language alone would put
    ``python 3.11`` and ``python 3.13`` on one queue, where whichever worker
    polled first would execute the test and the carefully-resolved version
    would be silently ignored.

    A version-less service keeps the plain ``testing-<language>`` name, so
    single-version installations are unaffected.

    Deliberately a pure function of its inputs so the API and the operator can
    derive the same name independently — the worker is started with
    ``--queues=<this>``.
    """
    queue = f"{TASK_QUEUE_PREFIX}-{_queue_token(language)}"
    if language_version and language_version.strip():
        queue = f"{queue}-{_queue_token(language_version)}"
    return queue


def _config_str(service, key: str) -> Optional[str]:
    if service.config and isinstance(service.config, dict):
        value = service.config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
        if key == "language_version" and isinstance(value, (int, float)):
            # A number here means the YAML was written unquoted. That is lossy
            # and cannot be undone: `language_version: 3.10` parses as the float
            # 3.1, so it will never match an example asking for "3.10". Warn
            # rather than mismatch in silence.
            if isinstance(value, float):
                logger.warning(
                    "Service '%s' has language_version: %s written as a NUMBER. "
                    "YAML reads 3.10 as 3.1, so version matching will misbehave — "
                    "quote it: language_version: \"%s\".",
                    getattr(service, "name", "?"), value, value,
                )
            return str(value)
    return None


def service_language(service) -> Optional[str]:
    """``Service.config.language``, or None."""
    return _config_str(service, "language")


def service_language_version(service) -> Optional[str]:
    """``Service.config.language_version``, or None.

    Set this when you run more than one version of a language side by side; it
    both selects the service (examples may request a ``version``) and separates
    the workers' queues.
    """
    return _config_str(service, "language_version")


def resolve_task_queue(
    service,
    service_type,
    *,
    require_testing_path: bool = True,
) -> str:
    """Resolve the Temporal task queue for a testing service.

    Order:
      1. an explicit ``service.config.temporal.task_queue`` (always wins, so
         existing deployments and any bespoke topology are untouched);
      2. otherwise ``testing-<config.language>``.

    The fallback exists because "one worker per language" is the intended
    shape, and making the queue a third independently-typed string meant a
    typo, or a queue nobody deployed, was accepted silently. Deriving it means
    a service that declares ``language: octave`` routes to ``testing-octave``
    with nothing further to configure.

    With ``require_testing_path`` the service type path must start with
    ``testing.`` (student test runs); tutor tests skip that check.
    """
    if require_testing_path and not str(service_type.path).startswith("testing."):
        raise BadRequestException(
            error_code="TASK_003",
            detail=f"Service type '{service_type.path}' is not a testing service. "
                   f"Expected path starting with 'testing.', got '{service_type.path}'"
        )

    task_queue = None
    if service.config and isinstance(service.config, dict):
        temporal_config = service.config.get("temporal", {})
        if isinstance(temporal_config, dict):
            task_queue = temporal_config.get("task_queue")

        # Warn about common misconfiguration - task_queue at root level
        if not task_queue and "task_queue" in service.config:
            logger.warning(
                f"Service '{service.name}' has task_queue at root level. "
                f"It should be nested under 'temporal': {{'temporal': {{'task_queue': 'queue-name'}}}}"
            )

    if not task_queue:
        language = service_language(service)
        if language:
            version = service_language_version(service)
            task_queue = default_task_queue_for_language(language, version)
            logger.info(
                "Service '%s' declares no task_queue; routing to '%s' by language "
                "'%s'%s",
                service.name, task_queue, language,
                f" version '{version}'" if version else "",
            )

    if not task_queue:
        config_example = {
            "language": "octave",
            "temporal": {"task_queue": "testing-octave"},
        }
        raise BadRequestException(
            error_code="EXT_005",
            detail=(
                f"Testing service '{service.name}' is not properly configured: it "
                f"declares neither a language nor a task queue, so there is no way "
                f"to route its tests. Set config.language (the queue is then "
                f"derived as 'testing-<language>'), or name a queue explicitly: "
                f"{json.dumps(config_example, indent=2)}"
            )
        )

    # Warn if using default queue for specialized testing service
    if task_queue == "computor-tasks" and "matlab" in service.name.lower():
        logger.warning(
            f"Service '{service.name}' appears to be a MATLAB testing service but is using the default queue. "
            f"Consider using a specialized queue like 'testing-matlab'"
        )

    return task_queue


def service_config_payload(service) -> dict:
    """Service block passed to testing workflows."""
    return {
        "id": str(service.id),
        "slug": service.slug,
        "name": service.name,
        "config": service.config or {},
    }


def service_type_config_payload(service_type) -> dict:
    """Service-type block passed to testing workflows."""
    return {
        "id": str(service_type.id),
        "path": str(service_type.path),
        "schema": service_type.schema or {},
        "properties": service_type.properties or {},
    }


def build_testing_submission(
    *,
    task_name: str,
    workflow_id: str,
    parameters: dict,
    queue: str,
):
    """Build the TaskSubmission for a testing workflow."""
    from computor_backend.tasks import TaskSubmission

    return TaskSubmission(
        task_name=task_name,
        workflow_id=workflow_id,
        parameters=parameters,
        queue=queue,
    )


async def dispatch_submission_test(
    artifact: SubmissionArtifact, db: Session
) -> Optional[Result]:
    """Fire the test run an official submission is entitled to.

    A submitted artifact with no Result is a dead end: the editor shows a
    submission with no outcome and nothing ever grades it (#311, #271). The
    normal editor flow tests first and then flips ``submit``; this guard covers
    every other way an artifact ends up submitted untested — the editor not
    knowing the content's testing service at that moment being the observed
    one (``testing_service_id`` is a lazily-backfilled cache and can be NULL).

    Best-effort by design: a submission must never fail because its test could
    not be dispatched, so every impossibility (no service, no deployment, the
    version already tested, a lost race) logs and returns None. The submission
    was already paid for by the caller's quota check; this run is that
    submission's test, so no further budget is charged here.
    """
    try:
        return await _dispatch_submission_test(artifact, db)
    except Exception:
        db.rollback()
        logger.exception(
            "Could not dispatch the submission test for artifact %s", artifact.id
        )
        return None


async def _dispatch_submission_test(
    artifact: SubmissionArtifact, db: Session
) -> Optional[Result]:
    from computor_backend.model.course import CourseMember
    from computor_backend.model.deployment import CourseContentDeployment
    from computor_backend.model.service import ServiceType

    # Already tested (the normal editor flow, or an earlier dispatch).
    if db.query(Result.id).filter(
        Result.submission_artifact_id == artifact.id
    ).first() is not None:
        return None

    submission_group = artifact.submission_group
    course_content = submission_group.course_content if submission_group else None
    if course_content is None:
        logger.warning(
            "Artifact %s has no course content; submission stays untested",
            artifact.id,
        )
        return None

    version_identifier = artifact.version_identifier or (
        (artifact.properties or {}).get("commit")
    )
    if not version_identifier:
        logger.warning(
            "Artifact %s has no version identifier; submission stays untested",
            artifact.id,
        )
        return None

    course_member = db.query(CourseMember).filter(
        CourseMember.id == artifact.uploaded_by_course_member_id
    ).first()
    if course_member is None:
        logger.warning(
            "Artifact %s has no uploading course member; submission stays untested",
            artifact.id,
        )
        return None

    # Same-version guard as ``create_test_run``: a byte-identical re-upload is a
    # different artifact with the same version identifier, and its result counts.
    already_tested = db.query(Result.id).filter(
        Result.course_member_id == course_member.id,
        Result.version_identifier == version_identifier,
        Result.course_content_id == course_content.id,
        Result.status.notin_(RETRYABLE_STATUSES),
    ).first()
    if already_tested is not None:
        return None

    from computor_backend.business_logic.testing_service import resolve_testing_service

    service = resolve_testing_service(course_content, db)
    if service is None:
        logger.warning(
            "No enabled testing service resolves for content %s; submission %s stays untested",
            course_content.id, artifact.id,
        )
        return None

    service_type = db.query(ServiceType).filter(
        ServiceType.id == service.service_type_id
    ).first()
    if service_type is None:
        logger.warning(
            "Service %s has no service type; submission %s stays untested",
            service.id, artifact.id,
        )
        return None

    deployment = db.query(CourseContentDeployment).filter(
        CourseContentDeployment.course_content_id == course_content.id
    ).first()
    if deployment is None or deployment.example_version_id is None:
        logger.warning(
            "Content %s has no deployed example version; submission %s stays untested",
            course_content.id, artifact.id,
        )
        return None

    task_queue = resolve_task_queue(service, service_type)

    from computor_backend.tasks.queue_health import assert_queue_has_worker

    await assert_queue_has_worker(task_queue, service.name)

    workflow_id = f"student-testing-{uuid4()}"
    job = {
        "user_id": str(course_member.user_id),
        "course_member_id": str(course_member.id),
        "course_content_id": str(course_content.id),
        "testing_service_id": str(service.id),
        "testing_service_slug": service.slug,
        "testing_service_type_path": str(service_type.path),
        "example_version_id": str(deployment.example_version_id),
        "artifact_id": str(artifact.id),
        "version_identifier": version_identifier,
    }

    result = Result(
        submission_artifact_id=artifact.id,
        submission_group_id=submission_group.id,
        course_member_id=course_member.id,
        course_content_id=course_content.id,
        course_content_type_id=course_content.course_content_type_id,
        testing_service_id=service.id,
        test_system_id=workflow_id,
        status=map_task_status_to_int(TaskStatus.QUEUED),
        grade=0.0,
        result=0,
        properties=None,
        version_identifier=version_identifier,
        reference_version_identifier=deployment.version_identifier,
    )
    db.add(result)
    try:
        db.commit()
    except IntegrityError:
        # A racing request created the result; that one's workflow runs.
        db.rollback()
        return None
    db.refresh(result)

    from computor_backend.tasks.temporal_executor import get_task_executor

    try:
        task_executor = get_task_executor()
        submission = build_testing_submission(
            task_name="student_testing",
            workflow_id=workflow_id,
            parameters={
                "test_job": job,
                "service_config": service_config_payload(service),
                "service_type_config": service_type_config_payload(service_type),
                "result_id": str(result.id),
            },
            queue=task_queue,
        )
        await task_executor.submit_task(submission)
    except Exception:
        logger.exception(
            "Task submission failed for submission-test Result %s", result.id
        )
        result.status = map_task_status_to_int(TaskStatus.FAILED)
        db.commit()
        return result

    logger.info(
        "Dispatched the submission test for artifact %s (result %s, queue %s)",
        artifact.id, result.id, task_queue,
    )
    return result
