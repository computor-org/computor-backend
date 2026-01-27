import os
import logging
import uuid as uuid_module
from uuid import UUID
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.redis_cache import get_cache, get_redis_client
from computor_backend.cache import Cache
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.auth import get_current_principal
from computor_backend.api.exceptions import NotFoundException, ForbiddenException, NotImplementedException, BadRequestException
from computor_backend.permissions.core import check_course_permissions
from computor_backend.services.storage_service import get_storage_service
from computor_backend.model.course import CourseContent, CourseMember, Course
from computor_backend.model.service import Service, ServiceType
from computor_backend.model.deployment import CourseContentDeployment
from computor_types.student_courses import CourseStudentQuery

logger = logging.getLogger(__name__)
from computor_types.student_course_contents import (
    CourseContentStudentList,
    CourseContentStudentQuery,
    CourseContentStudentGet,
)
from computor_types.tutor_course_members import TutorCourseMemberGet, TutorCourseMemberList
from computor_types.tutor_courses import CourseTutorGet, CourseTutorList
from computor_types.tutor_grading import TutorGradeCreate, TutorGradeResponse
from computor_types.course_members import CourseMemberQuery
from computor_types.tutor_submission_groups import (
    TutorSubmissionGroupGet,
    TutorSubmissionGroupList,
    TutorSubmissionGroupQuery,
)

# Import business logic
from computor_backend.business_logic.tutor import (
    get_tutor_course_content,
    list_tutor_course_contents,
    update_tutor_course_content_grade,
    get_tutor_course,
    list_tutor_courses,
    get_tutor_course_member,
    list_tutor_course_members,
    get_tutor_submission_group,
    list_tutor_submission_groups,
)

tutor_router = APIRouter()

@tutor_router.get("/course-members/{course_member_id}/course-contents/{course_content_id}", response_model=CourseContentStudentGet)
async def tutor_get_course_contents_endpoint(
    course_content_id: UUID | str,
    course_member_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    cache: Cache = Depends(get_cache)
):
    """Get course content for a course member as a tutor."""
    return await get_tutor_course_content(course_member_id, course_content_id, permissions, cache)

@tutor_router.get("/course-members/{course_member_id}/course-contents", response_model=list[CourseContentStudentList])
async def tutor_list_course_contents_endpoint(
    course_member_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseContentStudentQuery = Depends(),
    cache: Cache = Depends(get_cache)
):
    """List course contents for a course member as a tutor."""
    return await list_tutor_course_contents(course_member_id, permissions, params, cache)

@tutor_router.patch("/course-members/{course_member_id}/course-contents/{course_content_id}", response_model=TutorGradeResponse)
async def tutor_update_course_contents_endpoint(
    course_content_id: UUID | str,
    course_member_id: UUID | str,
    grade_data: TutorGradeCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """Update grade for a course content as a tutor."""
    return await update_tutor_course_content_grade(
        course_member_id=course_member_id,
        course_content_id=course_content_id,
        grade_value=grade_data.grade,
        grading_status=grade_data.status,
        feedback=grade_data.feedback,
        artifact_id=grade_data.artifact_id,
        permissions=permissions,
        db=db,
        cache=cache,
    )

@tutor_router.get("/courses/{course_id}", response_model=CourseTutorGet)
def tutor_get_courses_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    cache: Cache = Depends(get_cache)
):
    """Get a course for tutors."""
    return get_tutor_course(course_id, permissions, cache)

@tutor_router.get("/courses", response_model=list[CourseTutorList])
def tutor_list_courses_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseStudentQuery = Depends(),
    cache: Cache = Depends(get_cache)
):
    """List courses for tutors."""
    return list_tutor_courses(permissions, params, cache)

@tutor_router.get("/course-members/{course_member_id}", response_model=TutorCourseMemberGet)
def tutor_get_course_members_endpoint(
    course_member_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """Get a course member with unreviewed course contents."""
    return get_tutor_course_member(course_member_id, permissions, db, cache)

@tutor_router.get("/course-members", response_model=list[TutorCourseMemberList])
def tutor_list_course_members_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseMemberQuery = Depends(),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """List course members for tutors."""
    return list_tutor_course_members(permissions, params, db, cache)

## Submission Groups Endpoints

@tutor_router.get("/submission-groups/{submission_group_id}", response_model=TutorSubmissionGroupGet)
def tutor_get_submission_group_endpoint(
    submission_group_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """Get a submission group with detailed information for tutors."""
    return get_tutor_submission_group(submission_group_id, permissions, db, cache)

@tutor_router.get("/submission-groups", response_model=list[TutorSubmissionGroupList])
def tutor_list_submission_groups_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: TutorSubmissionGroupQuery = Depends(),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """List submission groups for tutors with filtering options.

    Query parameters:
    - course_id: Filter by course ID
    - course_content_id: Filter by course content ID
    - course_group_id: Filter by course group ID
    - has_submissions: Filter groups with/without submissions
    - has_ungraded_submissions: Filter groups with/without ungraded submissions
    - limit: Maximum number of results (default: 100)
    - offset: Number of results to skip (default: 0)
    """
    return list_tutor_submission_groups(permissions, params, db, cache)

## Helper function to get example version for a course content

async def _get_example_version_for_course_content(
    course_content_id: UUID | str,
    permissions: Principal,
    db: Session,
    cache: Cache,
):
    """
    Get the example version associated with a course content.

    Checks tutor permissions and resolves the example version from deployment or legacy field.

    Returns:
        Tuple of (course_content, example_version, repository)

    Raises:
        NotFoundException: If course content or example version not found
        ForbiddenException: If user doesn't have tutor permissions
    """
    from computor_backend.model.deployment import CourseContentDeployment
    from computor_backend.repositories.example_version_repo import ExampleVersionRepository

    # Get course content
    course_content = db.query(CourseContent).filter(
        CourseContent.id == course_content_id
    ).first()

    if not course_content:
        raise NotFoundException(detail=f"Course content {course_content_id} not found")

    # Check tutor permissions for the course
    user_id = permissions.get_user_id()
    if user_id and not permissions.is_admin:
        has_tutor_perms = check_course_permissions(
            permissions, CourseMember, "_tutor", db
        ).filter(
            CourseMember.course_id == course_content.course_id,
            CourseMember.user_id == user_id
        ).first()

        if not has_tutor_perms:
            raise ForbiddenException(
                detail="You don't have tutor permissions for this course"
            )

    # Check for deployment first (newer approach), then fall back to example_version_id (deprecated)
    deployment = db.query(CourseContentDeployment).filter(
        CourseContentDeployment.course_content_id == course_content_id
    ).order_by(CourseContentDeployment.assigned_at.desc()).first()

    example_version_id = None

    if deployment and deployment.example_version_id:
        example_version_id = deployment.example_version_id
    elif course_content.example_version_id:
        example_version_id = course_content.example_version_id

    if not example_version_id:
        raise NotFoundException(
            detail=f"No reference/example deployment found for this course content"
        )

    # Get the example version with relationships loaded
    version_repo = ExampleVersionRepository(db, cache)
    version = version_repo.get_with_relationships(example_version_id)

    if not version:
        raise NotFoundException(detail=f"Example version {example_version_id} not found")

    example = version.example
    repository = example.repository

    # Only support MinIO/S3 repositories
    if repository.source_type == "git":
        raise NotImplementedException("Git download not implemented - use git clone instead")

    if repository.source_type not in ["minio", "s3"]:
        raise BadRequestException(f"Download not supported for {repository.source_type} repositories")

    return course_content, version, repository


## Reference/Example Download Endpoint

@tutor_router.get(
    "/course-contents/{course_content_id}/reference",
    responses={200: {"content": {"application/zip": {}}}},
)
async def download_course_content_reference(
    course_content_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    storage_service = Depends(get_storage_service),
):
    """
    Download the reference/example solution for a course content as a ZIP file.

    This endpoint allows tutors to download the reference solution files
    associated with an assignment for grading purposes.

    The files included are determined by the meta.yaml properties:
    - properties.studentSubmissionFiles: Files that students must submit
    - properties.additionalFiles: Additional files provided to students

    These can be individual files or directories.

    Returns:
        StreamingResponse containing a ZIP file with the reference solution files
    """
    import zipfile
    import io
    import yaml

    course_content, version, repository = await _get_example_version_for_course_content(
        course_content_id, permissions, db, cache
    )

    # Parse meta.yaml to get reference file paths
    meta_data = yaml.safe_load(version.meta_yaml) if version.meta_yaml else {}
    properties = meta_data.get('properties', {})

    # Get the reference file patterns from meta.yaml
    student_submission_files = properties.get('studentSubmissionFiles', []) or []
    additional_files = properties.get('additionalFiles', []) or []
    reference_paths = set(student_submission_files + additional_files)

    if not reference_paths:
        raise NotFoundException(
            detail="No reference files defined in meta.yaml (studentSubmissionFiles or additionalFiles)"
        )

    # Create ZIP file in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Get bucket name and list objects
        bucket_name = repository.source_url.split('/')[0]

        objects = await storage_service.list_objects(
            bucket_name=bucket_name,
            prefix=version.storage_path,
        )

        for obj in objects:
            if obj.object_name.endswith('/'):
                continue  # Skip directory markers

            # Get relative filename within the example
            filename = obj.object_name.replace(f"{version.storage_path}/", "")

            # Check if this file matches any of the reference paths
            # A reference path can be a file or a directory prefix
            should_include = False
            for ref_path in reference_paths:
                if filename == ref_path:
                    # Exact file match
                    should_include = True
                    break
                elif filename.startswith(ref_path.rstrip('/') + '/'):
                    # File is inside a reference directory
                    should_include = True
                    break

            if not should_include:
                continue

            # Download file content
            file_data = await storage_service.download_file(
                bucket_name=bucket_name,
                object_key=obj.object_name,
            )

            # Add to ZIP
            zip_file.writestr(filename, file_data)

    # Seek to beginning of buffer
    zip_buffer.seek(0)

    # Create filename
    safe_title = course_content.title.replace(' ', '_').replace('/', '_')
    filename = f"{safe_title}_reference.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


## Content/Description Download Endpoint

@tutor_router.get(
    "/course-contents/{course_content_id}/description",
    responses={200: {"content": {"application/zip": {}}}},
)
async def download_course_content_description(
    course_content_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    storage_service = Depends(get_storage_service),
):
    """
    Download the content/description files for a course content as a ZIP file.

    This endpoint allows tutors to download the assignment description files
    which are stored in the 'content/' directory of the example.

    This typically includes:
    - index_<language_id>.md files (assignment descriptions in different languages)
    - mediaFiles/ directory (images, attachments, etc.)
    - Other supporting content files

    Returns:
        StreamingResponse containing a ZIP file with the content/ directory
    """
    import zipfile
    import io

    course_content, version, repository = await _get_example_version_for_course_content(
        course_content_id, permissions, db, cache
    )

    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    files_added = 0

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Get bucket name and list objects
        bucket_name = repository.source_url.split('/')[0]

        objects = await storage_service.list_objects(
            bucket_name=bucket_name,
            prefix=version.storage_path,
        )

        for obj in objects:
            if obj.object_name.endswith('/'):
                continue  # Skip directory markers

            # Get relative filename within the example
            filename = obj.object_name.replace(f"{version.storage_path}/", "")

            # Only include files from the content/ directory
            if not filename.startswith('content/'):
                continue

            # Download file content
            file_data = await storage_service.download_file(
                bucket_name=bucket_name,
                object_key=obj.object_name,
            )

            # Strip the 'content/' prefix so files are at root level in ZIP
            zip_filename = filename[len('content/'):]
            zip_file.writestr(zip_filename, file_data)
            files_added += 1

    if files_added == 0:
        raise NotFoundException(
            detail="No content files found in 'content/' directory for this course content"
        )

    # Seek to beginning of buffer
    zip_buffer.seek(0)

    # Create filename
    safe_title = course_content.title.replace(' ', '_').replace('/', '_')
    filename = f"{safe_title}_description.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

## MR-based course-content messages removed (deprecated)

## Comments routes moved to generic /course-member-comments

# ==============================================================================
# Tutor Testing Endpoints
# ==============================================================================
# These endpoints allow tutors to test their own code against assignment references.
# Unlike student testing, tutor tests:
# - Don't create database records (state in Redis only)
# - Store files in 'tutor-tests' bucket (with lifecycle cleanup)
# - Are ephemeral (1 hour TTL)
# ==============================================================================

from computor_types.tutor_tests import (
    TutorTestConfig,
    TutorTestCreateResponse,
    TutorTestStatus,
    TutorTestGet,
    TutorTestArtifactList,
    TutorTestArtifactInfo,
)


async def _check_tutor_permission_for_course_content(
    course_content_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> tuple[CourseContent, Course]:
    """
    Check that user has tutor (or higher) permissions for the course content.

    Returns:
        Tuple of (course_content, course)

    Raises:
        NotFoundException: If course content not found
        ForbiddenException: If user doesn't have tutor permissions
    """
    # Get course content
    course_content = db.query(CourseContent).filter(
        CourseContent.id == course_content_id
    ).first()

    if not course_content:
        raise NotFoundException(detail=f"Course content {course_content_id} not found")

    # Get course
    course = db.query(Course).filter(Course.id == course_content.course_id).first()
    if not course:
        raise NotFoundException(detail=f"Course not found")

    # Check tutor permissions for the course
    user_id = permissions.get_user_id()
    if user_id and not permissions.is_admin:
        has_tutor_perms = check_course_permissions(
            permissions, CourseMember, "_tutor", db
        ).filter(
            CourseMember.course_id == course_content.course_id,
            CourseMember.user_id == user_id
        ).first()

        if not has_tutor_perms:
            raise ForbiddenException(
                detail="You don't have tutor permissions for this course"
            )

    return course_content, course


@tutor_router.post(
    "/course-contents/{course_content_id}/test",
    response_model=TutorTestCreateResponse,
)
async def create_tutor_test(
    course_content_id: UUID | str,
    file: UploadFile = File(..., description="ZIP file containing tutor's code"),
    config: Optional[str] = Form(None, description="Optional JSON configuration"),
    permissions: Annotated[Principal, Depends(get_current_principal)] = None,
    db: Session = Depends(get_db),
    redis = Depends(get_redis_client),
):
    """
    Create and execute a tutor test for an assignment.

    This endpoint allows tutors to test their own code against the reference
    solution (test.yaml) for an assignment. Unlike student tests, tutor tests:

    - Don't create database records (state in Redis only)
    - Are ephemeral (automatically cleaned up after 1 hour)
    - Don't affect grading or submission history

    The tutor uploads a ZIP file containing their code (matching the structure
    expected by studentSubmissionFiles in meta.yaml), and the system runs the
    same tests that students would run.

    **Permissions**: Requires tutor role or higher for the course.

    **Request**:
    - `file`: ZIP file with tutor's code (multipart/form-data)
    - `config`: Optional JSON string with configuration:
      - `store_graphics_artifacts`: bool (default: true)
      - `timeout_seconds`: int (optional, uses service default)

    **Response**: Returns test_id for polling status via GET /tutors/tests/{test_id}
    """
    import json

    # Check permissions
    course_content, course = await _check_tutor_permission_for_course_content(
        course_content_id, permissions, db
    )

    # Parse optional config
    test_config = TutorTestConfig()
    if config:
        try:
            config_data = json.loads(config)
            test_config = TutorTestConfig(**config_data)
        except (json.JSONDecodeError, Exception) as e:
            raise BadRequestException(detail=f"Invalid config JSON: {e}")

    # Validate file is a ZIP
    if not file.filename or not file.filename.lower().endswith('.zip'):
        raise BadRequestException(detail="File must be a ZIP archive")

    # Check testing service is configured
    if not course_content.testing_service_id:
        raise BadRequestException(
            detail="Testing service not configured for this assignment"
        )

    # Get testing service and service type
    service = db.query(Service).filter(
        Service.id == course_content.testing_service_id
    ).first()

    if not service:
        raise BadRequestException(detail="Testing service not found")

    service_type = db.query(ServiceType).filter(
        ServiceType.id == service.service_type_id
    ).first()

    if not service_type:
        raise BadRequestException(detail="Service type not found")

    # Get deployment for example version
    deployment = db.query(CourseContentDeployment).filter(
        CourseContentDeployment.course_content_id == course_content_id
    ).order_by(CourseContentDeployment.assigned_at.desc()).first()

    example_version_id = None
    if deployment and deployment.example_version_id:
        example_version_id = str(deployment.example_version_id)
    elif course_content.example_version_id:
        example_version_id = str(course_content.example_version_id)

    if not example_version_id:
        raise BadRequestException(
            detail="No reference/example deployment found for this assignment"
        )

    # Generate test ID
    test_id = str(uuid_module.uuid4())

    # Read uploaded file
    zip_data = await file.read()

    # Store input files in MinIO
    from computor_backend.services.tutor_test_storage import store_tutor_test_input
    await store_tutor_test_input(test_id, zip_data)

    # Create Redis entry
    from computor_backend.services.tutor_test_state import create_tutor_test_entry
    user_id = permissions.get_user_id()

    entry = await create_tutor_test_entry(
        redis_client=redis,
        test_id=test_id,
        user_id=user_id,
        course_content_id=course_content_id,
        testing_service_id=service.id,
        testing_service_slug=service.slug,
        course_id=course.id,
    )

    # Start Temporal workflow
    from computor_backend.tasks import get_task_executor, TaskSubmission

    workflow_id = f"tutor-testing-{test_id}"

    # Get task queue from service config
    task_queue = "computor-tasks"
    if service.config and isinstance(service.config, dict):
        task_queue = service.config.get("task_queue", task_queue)
    elif service_type.properties and isinstance(service_type.properties, dict):
        task_queue = service_type.properties.get("task_queue", task_queue)

    # Prepare workflow parameters
    # Note: api_config is read from environment in the workflow (same as StudentTestingWorkflow)
    task_submission = TaskSubmission(
        task_name="tutor_testing",
        workflow_id=workflow_id,
        parameters={
            "test_id": test_id,
            "example_version_id": example_version_id,
            "service_type_config": {
                "id": str(service_type.id),
                "path": str(service_type.path),
                "schema": service_type.schema or {},
                "properties": service_type.properties or {},
            },
            "test_config": {
                "testing_service_slug": service.slug,
                "testing_service_id": str(service.id),
                "course_content_id": str(course_content_id),
                "user_id": str(user_id),
                "store_graphics_artifacts": test_config.store_graphics_artifacts,
            },
        },
        queue=task_queue,
    )

    try:
        task_executor = get_task_executor()
        await task_executor.submit_task(task_submission)
        logger.info(f"Started tutor test workflow {workflow_id} for test {test_id}")
    except Exception as e:
        logger.error(f"Failed to start tutor test workflow: {e}")
        raise BadRequestException(detail=f"Failed to start test: {e}")

    return TutorTestCreateResponse(
        test_id=test_id,
        status="pending",
        created_at=entry["created_at"],
    )


async def _get_tutor_test_info_and_sync(
    test_id: str,
    redis,
    permissions: Principal,
) -> tuple[dict, str, list]:
    """
    Get tutor test info from Redis, sync with MinIO if needed, and check permissions.

    Returns:
        Tuple of (test_info, current_status, artifacts)
    """
    from computor_backend.services.tutor_test_state import (
        get_tutor_test_full,
        update_tutor_test_status,
        store_tutor_test_result,
        TutorTestStatus as TutorTestStatusEnum,
    )
    from computor_backend.services.tutor_test_storage import (
        list_tutor_test_artifacts,
        get_tutor_test_result_from_minio,
    )
    from datetime import datetime, timezone

    # Get test info from Redis
    test_info = await get_tutor_test_full(redis, test_id)

    if not test_info:
        raise NotFoundException(detail=f"Tutor test {test_id} not found or expired")

    # Check if user owns this test
    user_id = permissions.get_user_id()
    if test_info.get("user_id") and str(user_id) != test_info.get("user_id"):
        if not permissions.is_admin:
            raise ForbiddenException(detail="You don't have access to this test")

    current_status = test_info.get("status", "pending")

    # If status is pending/running, check MinIO for results
    if current_status in ("pending", "running"):
        minio_result = await get_tutor_test_result_from_minio(test_id)

        if minio_result is not None:
            # Workflow completed - update Redis with results
            if minio_result.get("error"):
                status_enum = TutorTestStatusEnum.FAILED
            else:
                status_enum = TutorTestStatusEnum.COMPLETED

            await store_tutor_test_result(
                redis_client=redis,
                test_id=test_id,
                result=minio_result,
                status=status_enum,
            )

            test_info["status"] = status_enum.value
            test_info["result"] = minio_result
            test_info["finished_at"] = datetime.now(timezone.utc).isoformat()
            current_status = status_enum.value

        elif current_status == "pending":
            # Update to running if workflow has started
            await update_tutor_test_status(
                redis_client=redis,
                test_id=test_id,
                status=TutorTestStatusEnum.RUNNING,
                started_at=datetime.now(timezone.utc),
            )
            test_info["status"] = "running"
            current_status = "running"

    # Get artifact info
    artifacts = await list_tutor_test_artifacts(test_id)

    return test_info, current_status, artifacts


@tutor_router.get("/tests/{test_id}/status", response_model=TutorTestStatus)
async def get_tutor_test_status_endpoint(
    test_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    redis = Depends(get_redis_client),
):
    """
    Get quick status of a tutor test (for polling).

    Use this endpoint to poll for completion status.
    For full test results, use GET /tutors/tests/{test_id}.

    **Status values**:
    - `pending`: Test is queued
    - `running`: Test is executing
    - `completed`: Test finished successfully
    - `failed`: Test failed

    **Permissions**: Only the test owner or admin can check status.
    Tests are ephemeral and expire after 1 hour.
    """
    test_info, current_status, artifacts = await _get_tutor_test_info_and_sync(
        test_id, redis, permissions
    )

    return TutorTestStatus(
        test_id=test_id,
        status=current_status,
        created_at=test_info.get("created_at"),
        started_at=test_info.get("started_at"),
        finished_at=test_info.get("finished_at"),
        has_artifacts=len(artifacts) > 0,
        artifact_count=len(artifacts),
    )


@tutor_router.get("/tests/{test_id}", response_model=TutorTestGet)
async def get_tutor_test_endpoint(
    test_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    redis = Depends(get_redis_client),
):
    """
    Get full tutor test details including result_dict.

    Returns the complete test information including the full result_dict
    from MinIO (result.json). Use GET /tutors/tests/{test_id}/status for
    quick polling without the full result data.

    **Permissions**: Only the test owner or admin can access test details.
    Tests are ephemeral and expire after 1 hour.
    """
    test_info, current_status, artifacts = await _get_tutor_test_info_and_sync(
        test_id, redis, permissions
    )

    result_dict = test_info.get("result")

    # Extract convenience fields from result_dict
    passed = None
    failed = None
    total = None
    result_value = None
    error = None

    if result_dict:
        if "summary" in result_dict:
            passed = result_dict["summary"].get("passed")
            failed = result_dict["summary"].get("failed")
            total = result_dict["summary"].get("total")
        else:
            passed = result_dict.get("passed")
            failed = result_dict.get("failed")
            total = result_dict.get("total")

        result_value = result_dict.get("result_value")
        error = result_dict.get("error")

    return TutorTestGet(
        test_id=test_id,
        status=current_status,
        created_at=test_info.get("created_at"),
        started_at=test_info.get("started_at"),
        finished_at=test_info.get("finished_at"),
        result_dict=result_dict,
        passed=passed,
        failed=failed,
        total=total,
        result_value=result_value,
        error=error,
        has_artifacts=len(artifacts) > 0,
        artifact_count=len(artifacts),
    )


@tutor_router.get("/tests/{test_id}/artifacts", response_model=TutorTestArtifactList)
async def list_tutor_test_artifacts_endpoint(
    test_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    redis = Depends(get_redis_client),
):
    """
    List all artifacts from a tutor test.

    Returns metadata about each artifact file.

    **Permissions**: Only the test owner or admin can list artifacts.
    """
    from computor_backend.services.tutor_test_state import get_tutor_test_metadata
    from computor_backend.services.tutor_test_storage import list_tutor_test_artifacts

    # Check test exists and get metadata
    metadata = await get_tutor_test_metadata(redis, test_id)

    if not metadata:
        raise NotFoundException(detail=f"Tutor test {test_id} not found or expired")

    # Check permissions
    user_id = permissions.get_user_id()
    if metadata.get("user_id") and str(user_id) != metadata.get("user_id"):
        if not permissions.is_admin:
            raise ForbiddenException(detail="You don't have access to this test")

    # List artifacts
    artifacts = await list_tutor_test_artifacts(test_id)

    return TutorTestArtifactList(
        test_id=test_id,
        artifacts=[
            TutorTestArtifactInfo(
                filename=a["filename"],
                size=a["size"],
                last_modified=a.get("last_modified"),
            )
            for a in artifacts
        ],
        total_count=len(artifacts),
    )


@tutor_router.get(
    "/tests/{test_id}/artifacts/download",
    responses={200: {"content": {"application/zip": {}}}},
)
async def download_tutor_test_artifacts(
    test_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    redis = Depends(get_redis_client),
):
    """
    Download all artifacts from a tutor test as a ZIP file.

    Artifacts include generated files such as plots, figures, and debug output
    created during test execution.

    **Permissions**: Only the test owner or admin can download artifacts.
    """
    from computor_backend.services.tutor_test_state import get_tutor_test_metadata
    from computor_backend.services.tutor_test_storage import download_tutor_test_artifacts_as_zip

    # Check test exists and get metadata
    metadata = await get_tutor_test_metadata(redis, test_id)

    if not metadata:
        raise NotFoundException(detail=f"Tutor test {test_id} not found or expired")

    # Check permissions
    user_id = permissions.get_user_id()
    if metadata.get("user_id") and str(user_id) != metadata.get("user_id"):
        if not permissions.is_admin:
            raise ForbiddenException(detail="You don't have access to this test")

    # Download artifacts
    zip_data = await download_tutor_test_artifacts_as_zip(test_id)

    if not zip_data:
        raise NotFoundException(detail="No artifacts found for this test")

    from io import BytesIO
    zip_buffer = BytesIO(zip_data)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="tutor_test_{test_id}_artifacts.zip"'
        }
    )
