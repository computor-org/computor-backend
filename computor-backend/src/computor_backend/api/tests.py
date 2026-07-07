"""
Refactored tests API using the new artifact/test result pattern.
This module handles test execution for submission artifacts.
"""
from typing import Annotated, Optional
import logging
import uuid
from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session

from computor_backend.exceptions import BadRequestException, NotFoundException, RateLimitException
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.course_access import require_submission_group_access
from computor_backend.business_logic.testing_orchestration import (
    IN_PROGRESS_STATUSES,
    build_testing_submission,
    enforce_max_test_runs,
    find_active_test,
    resolve_artifact_for_test,
    resolve_task_queue,
    service_config_payload,
    service_type_config_payload,
    sync_result_status_from_temporal,
)
from computor_types.tasks import ResultStatus
from computor_backend.database import get_db
from computor_backend.redis_cache import get_redis_client, get_cache
from computor_backend.cache import Cache
from computor_backend.repositories import (
    ServiceTypeRepository,
    CourseContentDeploymentRepository,
)
from computor_types.results import ResultCreate, ResultList
from computor_types.repositories import Repository
from computor_types.tasks import TaskStatus, map_task_status_to_int
from computor_types.tests import TestCreate, TestJob
from computor_backend.model.artifact import SubmissionArtifact
from computor_backend.model.result import Result
from computor_backend.model.course import (
    Course, CourseContent, CourseContentType,
    CourseMember, SubmissionGroup, CourseFamily
)
from computor_backend.model.organization import Organization
from computor_backend.model.service import Service, ServiceType
from computor_backend.model.deployment import CourseContentDeployment
from computor_backend.model.example import Example, ExampleVersion
from computor_backend.custom_types import Ltree
from computor_backend.tasks import get_task_executor
from computor_types.tasks import map_int_to_task_status

logger = logging.getLogger(__name__)

tests_router = APIRouter()


def _has_result_permission(
    principal: Principal,
    action: str | list[str],
) -> bool:
    """Return True when principal has global permission on results."""
    return principal.is_admin or principal.permitted("result", action)

async def check_user_rate_limit(user_id: str, cache) -> bool:
    """
    Check user_id-based rate limiting using Redis.
    Returns True if limit exceeded, False otherwise.

    Limit: 1 test request per 1 second per user
    """
    try:
        rate_limit_key = f"rate_limit:user_id:{user_id}"
        current_count = await cache.get(rate_limit_key)

        if current_count is None:
            # First attempt, set counter with 1 second expiry
            await cache.set(rate_limit_key, "1", ex=1)
            return False
        else:
            count = int(current_count)
            if count >= 1:
                # Rate limit exceeded
                return True
            else:
                # Increment counter
                await cache.incr(rate_limit_key)
                return False
    except Exception as e:
        logger.error(f"Error checking user rate limit: {e}")
        # On error, allow the request (fail open)
        return False

@tests_router.post("", response_model=ResultList)
async def create_test_run(
    test_create: TestCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache = Depends(get_redis_client),
    repo_cache: Cache = Depends(get_cache),
):
    """
    Create and execute a test for a submission artifact.

    Ways to specify what to test:
    1. Provide artifact_id directly
    2. Provide submission_group_id + version_identifier to find specific version
    3. Provide submission_group_id only to test the latest submission

    Tests are executed via Temporal workflows.

    Rate Limits (to prevent test abuse):
    - 1 test request per 1 second per user

    Returns 429 Too Many Requests if limit is exceeded.
    """
    from computor_backend.database import set_db_user

    user_id = permissions.get_user_id()

    # Check user-based rate limit
    user_limit_exceeded = await check_user_rate_limit(str(user_id), cache)
    if user_limit_exceeded:
        raise RateLimitException(
            error_code="RATE_003",
            detail=f"Too many test requests. Please wait before submitting another test.",
            retry_after=1,
            context={
                "user_id": str(user_id),
                "limit": 1,
                "window_seconds": 1
            }
        )

    # Set user context for audit tracking
    set_db_user(db, user_id)

    # Determine which artifact to test
    artifact = resolve_artifact_for_test(test_create, db)

    # Get the submission group with permission check
    submission_group = check_course_permissions(
        permissions, SubmissionGroup, "_student", db
    ).filter(
        SubmissionGroup.id == artifact.submission_group_id
    ).first()

    if not submission_group:
        raise NotFoundException(
            error_code="SUBMIT_002",
            detail="Submission group not found or access denied"
        )

    # Get course member who is running the test
    course_member = db.query(CourseMember).filter(
        CourseMember.user_id == user_id,
        CourseMember.course_id == submission_group.course_id
    ).first()

    if not course_member:
        raise NotFoundException(
            error_code="NF_003",
            detail="You are not a member of this course"
        )

    # Test limitation: a member's earlier non-retryable test blocks a re-run
    existing_test = find_active_test(artifact.id, course_member.id, db)

    if existing_test:
        # Check if still running
        if existing_test.status in IN_PROGRESS_STATUSES:
            if await sync_result_status_from_temporal(existing_test, db):
                # Still running, return the existing one
                return ResultList.model_validate(existing_test)

        # If completed successfully, don't allow another test
        elif existing_test.status == int(ResultStatus.FINISHED):
            raise BadRequestException(
                error_code="SUBMIT_008",
                detail="You have already tested this artifact. "
                       "Multiple tests are not allowed unless the previous test crashed or was cancelled."
            )

    # Check max test runs limit for the submission group
    enforce_max_test_runs(artifact.id, submission_group, db, error_code="SUBMIT_004")

    # Get course content (assignment)
    course_content = db.query(CourseContent).filter(
        CourseContent.id == submission_group.course_content_id
    ).first()

    if not course_content:
        raise BadRequestException(
            error_code="SUBMIT_005",
            detail="Assignment not configured"
        )

    # Resolve the testing service: cached FK, else by the example's executionBackend
    # slug (self-healing). Lets a content/example exist before the service is
    # registered — testing works the moment the matching service appears.
    from computor_backend.business_logic.testing_service import resolve_testing_service

    service = resolve_testing_service(course_content, db)

    if not service:
        raise BadRequestException(
            error_code="SUBMIT_005",
            detail="Assignment has no testing service: no enabled service matches the example's executionBackend slug"
        )

    # Get the service type using repository
    service_type_repo = ServiceTypeRepository(db, repo_cache)
    service_type = service_type_repo.get_by_id_optional(str(service.service_type_id))

    if not service_type:
        raise BadRequestException(
            error_code="SUBMIT_005",
            detail="Service type not found for service"
        )

    # Get deployment info for reference example using repository
    deployment_repo = CourseContentDeploymentRepository(db, repo_cache)
    deployment = deployment_repo.find_by_content(str(course_content.id))

    if not deployment or not deployment.example_version_id:
        raise BadRequestException(
            error_code="DEPLOY_001",
            detail="Assignment not released: missing deployment or example version"
        )

    # Use version identifier from artifact
    artifact_properties = artifact.properties or {}
    version_identifier = (
        test_create.version_identifier or
        artifact.version_identifier or  # Use the proper column first
        artifact_properties.get('commit')  # Fallback for legacy data
    )

    if not version_identifier:
        raise BadRequestException(
            error_code="SUBMIT_006",
            detail="Version identifier (commit) is required"
        )

    # Create test job with new structure (using example_version_id and artifact_id)
    job = {
        "user_id": str(user_id),
        "course_member_id": str(course_member.id),
        "course_content_id": str(course_content.id),
        "testing_service_id": str(service.id),
        "testing_service_slug": service.slug,
        "testing_service_type_path": str(service_type.path),
        "example_version_id": str(deployment.example_version_id),
        "artifact_id": str(artifact.id),
        "version_identifier": version_identifier,
    }

    # Generate workflow ID
    workflow_id = f"student-testing-{str(uuid.uuid4())}"

    # Check for existing result with same (member, version, content)
    # This prevents unique constraint violations from the partial index
    existing_result = db.query(Result).filter(
        Result.course_member_id == course_member.id,
        Result.version_identifier == version_identifier,
        Result.course_content_id == course_content.id,
        Result.status.notin_([1, 2, 6])  # Not already FAILED(1), CANCELLED(2), or CRASHED(6)
    ).first()

    if existing_result:
        # Sync against Temporal; a stale row is corrected, a live one blocks
        workflow_still_running = await sync_result_status_from_temporal(
            existing_result, db, treat_missing_as_crashed=True
        )

        if workflow_still_running:
            raise BadRequestException(
                error_code="SUBMIT_003",
                detail=f"A test is already running for this version. Please wait for it to complete."
            )

    # Validate task queue configuration BEFORE creating the Result record
    # This prevents duplicate key errors when retrying with misconfigured services
    task_queue = resolve_task_queue(service, service_type)

    # Create test result record (only after validation passes)
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
    db.commit()
    db.refresh(result)

    # Start Temporal workflow for testing
    try:
        # Task queue has already been validated above
        task_executor = get_task_executor()

        task_submission = build_testing_submission(
            task_name="student_testing",
            workflow_id=workflow_id,
            parameters={
                "test_job": job,  # Already a dict, no need for model_dump()
                "service_config": service_config_payload(service),
                "service_type_config": service_type_config_payload(service_type),
                "result_id": str(result.id),
            },
            queue=task_queue,
        )

        submitted_id = await task_executor.submit_task(task_submission)

        if submitted_id != workflow_id:
            logger.warning(f"Submitted workflow ID {submitted_id} doesn't match pre-generated ID {workflow_id}")

    except Exception as e:
        # If task submission fails, update result status to FAILED
        logger.error(f"Task submission failed for Result {result.id}: {str(e)}")
        result.status = map_task_status_to_int(TaskStatus.FAILED)
        db.commit()
        db.refresh(result)
        raise

    return ResultList.model_validate(result)

@tests_router.get("/status/{result_id}")
async def get_test_status(
    result_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """Get the current status of a test execution.

    Permission rules:
    - Students can view their own test results (member of submission group)
    - Tutors and higher roles can view all test results in their courses
    """

    # Query only the fields we need, including join to get submission group for permissions
    result_data = db.query(
        Result.id,
        Result.status,
        Result.started_at,
        Result.test_system_id,
        Result.submission_artifact_id,
        SubmissionGroup.id.label("submission_group_id"),
        SubmissionGroup.course_id
    ).join(
        SubmissionArtifact, SubmissionArtifact.id == Result.submission_artifact_id
    ).join(
        SubmissionGroup, SubmissionGroup.id == SubmissionArtifact.submission_group_id
    ).filter(
        Result.id == result_id
    ).first()

    if not result_data:
        raise NotFoundException(
            error_code="NF_004",
            detail="Test result not found"
        )

    # Check permissions
    can_view_all = _has_result_permission(permissions, "get")
    if not can_view_all:
        require_submission_group_access(
            permissions, result_data.submission_group_id, result_data.course_id, db,
            detail="You don't have permission to view this test result",
            error_code="AUTHZ_003",
        )

    # If test has a workflow ID, check Temporal status for running tests
    status = result_data.status
    if result_data.test_system_id and status in IN_PROGRESS_STATUSES:
        result_row = db.query(Result).filter(Result.id == result_id).first()
        if result_row is not None:
            await sync_result_status_from_temporal(result_row, db, sync_in_progress=True)
            status = result_row.status

    return {
        "id": str(result_data.id),
        "status": map_int_to_task_status(status),
        "started_at": result_data.started_at,
    }
