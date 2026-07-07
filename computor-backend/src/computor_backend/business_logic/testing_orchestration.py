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
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from computor_backend.exceptions import BadRequestException, NotFoundException
from computor_backend.model.artifact import SubmissionArtifact
from computor_backend.model.result import Result
from computor_types.tasks import (
    ResultStatus,
    TaskStatus,
    map_task_status_to_int,
)

logger = logging.getLogger(__name__)

# A member's earlier test only stops a re-run while it is not in one of these
# states (a crashed/cancelled/failed run may always be retried).
RETRYABLE_STATUSES = (
    int(ResultStatus.FAILED),
    int(ResultStatus.CANCELLED),
    int(ResultStatus.CRASHED),
)

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


def enforce_max_test_runs(
    artifact_id: UUID | str,
    submission_group,
    db: Session,
    *,
    error_code: Optional[str] = None,
) -> None:
    """Raise when the submission group's ``max_test_runs`` is exhausted."""
    if submission_group.max_test_runs is None:
        return

    test_count = db.query(func.count(Result.id)).filter(
        Result.submission_artifact_id == artifact_id
    ).scalar()

    if test_count >= submission_group.max_test_runs:
        kwargs = {"error_code": error_code} if error_code else {}
        raise BadRequestException(
            detail=f"Maximum test runs ({submission_group.max_test_runs}) reached for this artifact",
            **kwargs,
        )


def enforce_test_limits(
    artifact: SubmissionArtifact,
    course_member_id: UUID | str,
    submission_group,
    db: Session,
) -> None:
    """Hard-fail variant of the test-limitation rules.

    Used where an existing active test is always an error (test-result
    ingestion); ``create_test_run`` instead syncs the old run against
    Temporal and may return it idempotently.
    """
    if find_active_test(artifact.id, course_member_id, db):
        raise BadRequestException(
            detail="You have already run a test on this artifact. "
                   "Multiple tests are not allowed unless the previous test crashed or was cancelled."
        )

    enforce_max_test_runs(artifact.id, submission_group, db)


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

    if not result.test_system_id:
        return False

    task_executor = get_task_executor()
    try:
        task_info = await task_executor.get_task_status(result.test_system_id)
    except Exception as e:
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


def resolve_task_queue(
    service,
    service_type,
    *,
    require_testing_path: bool = True,
) -> str:
    """Extract and validate the Temporal task queue for a testing service.

    The queue MUST live at ``service.config.temporal.task_queue``. With
    ``require_testing_path`` the service type path must start with
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
        config_example = {
            "temporal": {
                "task_queue": "testing-matlab",
                "max_retries": 3,
                "timeout_minutes": 30
            }
        }
        raise BadRequestException(
            error_code="EXT_005",
            detail=(
                f"Testing service '{service.name}' is not properly configured. "
                f"No task queue specified. Service configuration must include: "
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
