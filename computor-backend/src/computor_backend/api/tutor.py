from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.redis_cache import get_cache
from computor_backend.cache import Cache
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.auth import get_current_principal
from computor_backend.api.exceptions import NotFoundException, ForbiddenException, NotImplementedException, BadRequestException
from computor_backend.permissions.core import check_course_permissions
from computor_backend.services.storage_service import get_storage_service
from computor_backend.model.course import CourseContent, CourseMember
from computor_types.student_courses import CourseStudentQuery
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

## Reference/Example Download Endpoint

@tutor_router.get("/course-contents/{course_content_id}/reference")
async def download_course_content_reference(
    course_content_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    with_dependencies: bool = Query(False, description="Include all dependencies recursively"),
    storage_service = Depends(get_storage_service),
):
    """
    Download the reference/example solution for a course content as a ZIP file.

    This endpoint allows tutors to download the example/reference repository
    associated with an assignment for grading or reference purposes.

    Query parameters:
    - with_dependencies: Include all example dependencies recursively (default: False)

    Returns:
        StreamingResponse containing a ZIP file with the example files
    """
    import zipfile
    import io
    from fastapi.responses import StreamingResponse
    from computor_backend.model.deployment import CourseContentDeployment
    from computor_backend.model.example import ExampleVersion
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
                continue  # Skip directories

            # Get relative filename
            filename = obj.object_name.replace(f"{version.storage_path}/", "")

            # Filter out unwanted files and directories
            if filename.startswith('localTests/'):
                continue
            if filename in ['meta.yaml', 'test.yaml']:
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

## MR-based course-content messages removed (deprecated)

## Comments routes moved to generic /course-member-comments
