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
from computor_backend.api.exceptions import NotFoundException, ForbiddenException
from computor_backend.permissions.core import check_course_permissions
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
def tutor_get_course_contents_endpoint(
    course_content_id: UUID | str,
    course_member_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """Get course content for a course member as a tutor."""
    return get_tutor_course_content(course_member_id, course_content_id, permissions, db, cache)

@tutor_router.get("/course-members/{course_member_id}/course-contents", response_model=list[CourseContentStudentList])
def tutor_list_course_contents_endpoint(
    course_member_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseContentStudentQuery = Depends(),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """List course contents for a course member as a tutor."""
    return list_tutor_course_contents(course_member_id, permissions, params, db, cache)

@tutor_router.patch("/course-members/{course_member_id}/course-contents/{course_content_id}", response_model=TutorGradeResponse)
def tutor_update_course_contents_endpoint(
    course_content_id: UUID | str,
    course_member_id: UUID | str,
    grade_data: TutorGradeCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """Update grade for a course content as a tutor."""
    return update_tutor_course_content_grade(
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
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """Get a course for tutors."""
    return get_tutor_course(course_id, permissions, db, cache)

@tutor_router.get("/courses", response_model=list[CourseTutorList])
def tutor_list_courses_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseStudentQuery = Depends(),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """List courses for tutors."""
    return list_tutor_courses(permissions, params, db, cache)

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
):
    """
    Download the reference/example solution for a course content.

    This endpoint allows tutors to download the example/reference repository
    associated with an assignment for grading or reference purposes.

    Query parameters:
    - with_dependencies: Include all example dependencies recursively (default: False)
    """
    from computor_backend.repositories.example_version_repo import ExampleVersionRepository
    from computor_backend.api.examples import download_example_latest
    from computor_backend.services.storage_service import get_storage_service

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
    from computor_backend.model.deployment import CourseContentDeployment

    deployment = db.query(CourseContentDeployment).filter(
        CourseContentDeployment.course_content_id == course_content_id
    ).order_by(CourseContentDeployment.assigned_at.desc()).first()

    example_version = None

    if deployment and deployment.example_version_id:
        # Use deployment's example version (preferred method)
        from computor_backend.model.example import ExampleVersion
        example_version = db.query(ExampleVersion).filter(
            ExampleVersion.id == deployment.example_version_id
        ).first()
    elif course_content.example_version_id:
        # Fall back to deprecated direct example_version_id on course_content
        from computor_backend.model.example import ExampleVersion
        example_version = db.query(ExampleVersion).filter(
            ExampleVersion.id == course_content.example_version_id
        ).first()

    if not example_version:
        raise NotFoundException(
            detail=f"No reference/example deployment found for this course content"
        )

    # Download the example using the existing examples endpoint logic
    storage_service = get_storage_service()
    return await download_example_latest(
        example_id=str(example_version.example_id),
        with_dependencies=with_dependencies,
        db=db,
        permissions=permissions,
        storage_service=storage_service,
    )

## MR-based course-content messages removed (deprecated)

## Comments routes moved to generic /course-member-comments
