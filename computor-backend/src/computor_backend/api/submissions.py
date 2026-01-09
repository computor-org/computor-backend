"""API endpoints for submission artifacts, grading and reviews."""
import io
import logging
import zipfile
from datetime import datetime
from pathlib import PurePosixPath
from typing import Annotated, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Response, status, File, Form, UploadFile, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from computor_backend.api.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.database import get_db
from computor_backend.model.artifact import (
    SubmissionArtifact,
    SubmissionGrade,
    SubmissionReview,
)
from computor_backend.model.result import Result
from computor_backend.model.course import (
    CourseContent,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.services.storage_service import get_storage_service
from computor_backend.storage_security import perform_full_file_validation, sanitize_filename
from computor_backend.storage_config import MAX_UPLOAD_SIZE, format_bytes
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal
from computor_types.artifacts import (
    SubmissionArtifactList,
    SubmissionArtifactGet,
    SubmissionArtifactUpdate,
    SubmissionArtifactQuery,
    SubmissionGradeCreate,
    SubmissionGradeUpdate,
    SubmissionGradeListItem,
    SubmissionGradeDetail,
    SubmissionReviewCreate,
    SubmissionReviewUpdate,
    SubmissionReviewListItem,
)
from computor_types.results import (
    ResultCreate,
    ResultUpdate,
    ResultList,
    ResultGet,
    ResultArtifactInfo,
)
from computor_types.submissions import (
    SubmissionCreate,
    SubmissionUploadResponseModel,
)
from pydantic import ValidationError
from sqlalchemy import func
import re
import mimetypes

# Import business logic functions
from computor_backend.cache import Cache
from computor_backend.redis_cache import get_cache
from computor_backend.repositories.submission_artifact import SubmissionArtifactRepository
from computor_backend.repositories.result import ResultRepository
from computor_backend.business_logic.submissions import (
    upload_submission_artifact,
    check_artifact_access,
    get_artifact_with_details,
    update_artifact,
    create_artifact_grade,
    update_grade,
    delete_grade,
    create_artifact_review,
    update_review,
    delete_review,
    create_test_result,
    update_test_result,
    download_submission_as_zip,
)

logger = logging.getLogger(__name__)

submissions_router = APIRouter(prefix="/submissions", tags=["submissions"])
_DIR_ALLOWED_PATTERN = re.compile(r"[^A-Za-z0-9_.-]")


def _has_submission_artifact_permission(
    principal: Principal,
    action: str | list[str],
) -> bool:
    """Return True when principal has global permission for submission artifacts."""
    return principal.is_admin or principal.permitted("submission_artifact", action)

def _sanitize_path_segment(segment: str, *, is_file: bool = False) -> str:
    """Sanitize a path segment (directory or filename)."""
    segment = segment.strip()
    if not segment:
        return "file" if is_file else "dir"

    if is_file:
        sanitized = sanitize_filename(segment)
    else:
        sanitized = _DIR_ALLOWED_PATTERN.sub("_", segment)
        sanitized = sanitized.strip("._") or "dir"
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
    return sanitized

def _sanitize_archive_path(name: str) -> str:
    """Normalize and sanitize a path from inside a ZIP archive."""
    path = PurePosixPath(name)
    if path.is_absolute():
        raise BadRequestException("Archive entries must use relative paths")

    parts: List[str] = []
    for idx, part in enumerate(path.parts):
        if part in ("", "."):
            continue
        if part == "..":
            raise BadRequestException("Archive contains invalid path traversal sequences")
        parts.append(_sanitize_path_segment(part, is_file=(idx == len(path.parts) - 1)))

    if not parts:
        raise BadRequestException("Archive contains an empty file path")

    return "/".join(parts)

# ===============================
# Submission Upload Endpoint
# ===============================

@submissions_router.post("/artifacts", response_model=SubmissionUploadResponseModel, status_code=status.HTTP_201_CREATED)
async def upload_submission(
    submission_create: Annotated[str, Form(..., description="Submission metadata as JSON")],
    request: Request,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    file: UploadFile = File(..., description="Submission ZIP archive"),
    db: Session = Depends(get_db),
    storage_service = Depends(get_storage_service),
    cache: Cache = Depends(get_cache),
):
    """
    Upload a submission file to MinIO and create matching SubmissionArtifact records.

    Security & Limits:
    - Maximum file size: 10MB (configurable via MINIO_MAX_UPLOAD_SIZE env var)
    - Request body size enforced by middleware before processing
    - File validation: extension, MIME type, and content checks

    Performance Notes:
    - Entire file is read into memory for validation
    - For large files, this endpoint may take 5-15 seconds
    - Configure uvicorn timeout if needed: --timeout-keep-alive 300
    - Does NOT block other API requests (async processing)
    """

    try:
        submission_data = SubmissionCreate.model_validate_json(submission_create)
    except ValidationError as validation_error:
        raise BadRequestException(detail=f"Invalid submission metadata: {validation_error}") from validation_error

    # Read file content
    file_content = await file.read()

    # Delegate to business logic layer
    return await upload_submission_artifact(
        submission_group_id=submission_data.submission_group_id,
        file_content=file_content,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        version_identifier=submission_data.version_identifier,
        submit=submission_data.submit,
        permissions=permissions,
        db=db,
        storage_service=storage_service,
        cache=cache,
    )

# ===============================
# Artifact Listing Endpoints
# ===============================

@submissions_router.get("/artifacts", response_model=List[SubmissionArtifactList])
async def list_submission_artifacts(
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: SubmissionArtifactQuery = Depends(),
    course_content_id: Optional[str] = None,
    with_latest_result: bool = False,
    db: Session = Depends(get_db),
):
    """List submission artifacts with optional filtering.

    Query parameters:
    - submission_group_id: Filter by submission group
    - uploaded_by_course_member_id: Filter by uploader
    - content_type: Filter by content type
    - submit: Filter by official submissions (True) or test runs (False)
    - with_latest_result: If True, include latest successful result (status=0) for each artifact
    """

    can_list_all = _has_submission_artifact_permission(permissions, "list")
    user_id = permissions.get_user_id()

    query = db.query(SubmissionArtifact)

    # Filter by submission group if provided
    if params.submission_group_id:
        # Check permissions for this submission group
        submission_group = db.query(SubmissionGroup).filter(
            SubmissionGroup.id == params.submission_group_id
        ).first()

        if not submission_group:
            raise NotFoundException(detail="Submission group not found")

        # Check if user is a member of the submission group or has elevated permissions
        if user_id and not can_list_all:
            is_group_member = db.query(SubmissionGroupMember).join(
                CourseMember
            ).filter(
                SubmissionGroupMember.submission_group_id == params.submission_group_id,
                CourseMember.user_id == user_id
            ).first()

            if not is_group_member:
                # Check for tutor/instructor permissions in the course
                has_elevated_perms = check_course_permissions(
                    permissions, CourseMember, "_tutor", db
                ).filter(
                    CourseMember.course_id == submission_group.course_id,
                    CourseMember.user_id == user_id
                ).first()

                if not has_elevated_perms:
                    raise ForbiddenException(detail="You don't have permission to view these artifacts")
        query = query.filter(SubmissionArtifact.submission_group_id == params.submission_group_id)

    # Filter by course content if provided
    if course_content_id:
        # Get course_id for the course content to check permissions
        course_content = db.query(CourseContent).filter(
            CourseContent.id == course_content_id
        ).first()

        if not course_content:
            raise NotFoundException(detail="Course content not found")

        if user_id and not can_list_all:
            # Check for tutor/instructor permissions in the course
            has_elevated_perms = check_course_permissions(
                permissions, CourseMember, "_tutor", db
            ).filter(
                CourseMember.course_id == course_content.course_id,
                CourseMember.user_id == user_id
            ).first()

            if has_elevated_perms:
                # Tutor/Instructor: can see all artifacts for this course content
                query = query.join(SubmissionGroup).filter(
                    SubmissionGroup.course_content_id == course_content_id
                )
            else:
                # Student: only see artifacts from their own submission groups
                query = query.join(SubmissionGroup).join(
                    SubmissionGroupMember
                ).join(
                    CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id
                ).filter(
                    SubmissionGroup.course_content_id == course_content_id,
                    CourseMember.user_id == user_id
                )
        else:
            # Admin or scoped tokens: can see all artifacts for this course content
            query = query.join(SubmissionGroup).filter(
                SubmissionGroup.course_content_id == course_content_id
            )

    # Filter by version identifier if provided
    if params.version_identifier:
        query = query.filter(SubmissionArtifact.version_identifier == params.version_identifier)

    # Filter by submit flag if provided
    if params.submit is not None:
        query = query.filter(SubmissionArtifact.submit == params.submit)

    # Filter by uploaded_by_course_member_id if provided
    if params.uploaded_by_course_member_id:
        query = query.filter(SubmissionArtifact.uploaded_by_course_member_id == params.uploaded_by_course_member_id)

    # Filter by content_type if provided
    if params.content_type:
        query = query.filter(SubmissionArtifact.content_type == params.content_type)

    # Apply pagination
    total = query.count()
    artifacts = query.order_by(
        SubmissionArtifact.created_at.desc()
    ).limit(params.limit).offset(params.skip).all()

    response.headers["X-Total-Count"] = str(total)

    # Build response with optional latest result
    result_list = []
    for artifact in artifacts:
        artifact_dto = SubmissionArtifactList.model_validate(artifact, from_attributes=True)

        # Fetch latest successful result if requested
        if with_latest_result:
            latest_result = db.query(Result).filter(
                Result.submission_artifact_id == artifact.id,
                Result.status == 0  # FINISHED status
            ).order_by(
                Result.created_at.desc()
            ).first()

            if latest_result:
                from computor_types.results import ResultList
                artifact_dto.latest_result = ResultList.model_validate(latest_result, from_attributes=True)

        result_list.append(artifact_dto)

    return result_list

@submissions_router.get("/artifacts/{artifact_id}", response_model=SubmissionArtifactGet)
async def get_submission_artifact(
    artifact_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Get details of a specific submission artifact."""

    artifact = check_artifact_access(artifact_id, permissions, db)
    return get_artifact_with_details(artifact)

@submissions_router.patch("/artifacts/{artifact_id}", response_model=SubmissionArtifactGet)
async def update_submission_artifact(
    artifact_id: str,
    update_data: SubmissionArtifactUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
):
    """Update a submission artifact (e.g., change submit status)."""

    can_update = _has_submission_artifact_permission(permissions, "update")
    # Initialize repository with cache for automatic invalidation
    artifact_repo = SubmissionArtifactRepository(db, cache)

    artifact = db.query(SubmissionArtifact).options(
        joinedload(SubmissionArtifact.submission_group)
    ).filter(
        SubmissionArtifact.id == artifact_id
    ).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Check permissions - only group members or tutors/instructors can update
    user_id = permissions.get_user_id()
    if user_id and not can_update:
        is_group_member = db.query(SubmissionGroupMember).join(
            CourseMember
        ).filter(
            SubmissionGroupMember.submission_group_id == artifact.submission_group_id,
            CourseMember.user_id == user_id
        ).first()

        if not is_group_member:
            # Check for tutor/instructor permissions
            has_elevated_perms = check_course_permissions(
                permissions, CourseMember, "_tutor", db
            ).filter(
                CourseMember.course_id == artifact.submission_group.course_id,
                CourseMember.user_id == user_id
            ).first()

            if not has_elevated_perms:
                raise ForbiddenException(detail="You don't have permission to update this artifact")
    elif not can_update:
        raise ForbiddenException(detail="You don't have permission to update this artifact")

    # Build updates dict
    updates = {}
    if update_data.submit is not None:
        updates['submit'] = update_data.submit
    if update_data.properties is not None:
        updates['properties'] = update_data.properties

    # CRITICAL: Use repository.update() for automatic cache invalidation
    if updates:
        artifact = artifact_repo.update(str(artifact_id), updates)

    logger.info("Updated submission artifact %s (cache invalidated)", artifact_id)

    # Return updated artifact with computed fields
    artifact_get = SubmissionArtifactGet.model_validate(artifact)
    artifact_get.grades_count = len(artifact.grades) if hasattr(artifact, 'grades') else 0
    artifact_get.reviews_count = len(artifact.reviews) if hasattr(artifact, 'reviews') else 0
    artifact_get.test_results_count = len(artifact.test_results) if hasattr(artifact, 'test_results') else 0

    if hasattr(artifact, 'grades') and artifact.grades:
        grades = [g.grade for g in artifact.grades if g.grade is not None]
        artifact_get.average_grade = sum(grades) / len(grades) if grades else None

    return artifact_get

@submissions_router.get("/artifacts/download")
async def download_latest_submission(
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    submission_group_id: Optional[str] = None,
    course_content_id: Optional[str] = None,
    course_member_id: Optional[str] = None,
    version_identifier: Optional[str] = None,  # Optional
    submit_only: bool = True,  # Only download official submissions by default
    db: Session = Depends(get_db),
    storage_service = Depends(get_storage_service),
):
    """
    Download the latest submission artifact as a ZIP file.

    You must provide EITHER:
    - submission_group_id: Direct submission group ID
    OR
    - course_content_id + course_member_id: To find the submission group

    Optional filters:
    - version_identifier: Filter by specific version (e.g., "v1.0.0", "commit-abc123")
    - submit_only: Only include official submissions (submit=True), default: True
    """
    from fastapi.responses import StreamingResponse

    # Validate input: must provide either submission_group_id OR (course_content_id + course_member_id)
    if submission_group_id:
        if course_content_id or course_member_id:
            raise BadRequestException(
                detail="Provide either submission_group_id OR (course_content_id + course_member_id), not both"
            )

        # Find submission group by ID
        submission_group = db.query(SubmissionGroup).filter(
            SubmissionGroup.id == submission_group_id
        ).first()

        if not submission_group:
            raise NotFoundException(detail="Submission group not found")

    elif course_content_id and course_member_id:
        # Find submission group for this course member and course content
        submission_group = db.query(SubmissionGroup).join(
            SubmissionGroupMember
        ).filter(
            SubmissionGroup.course_content_id == course_content_id,
            SubmissionGroupMember.course_member_id == course_member_id
        ).first()

        if not submission_group:
            raise NotFoundException(detail="No submission group found for this course member and content")

    else:
        raise BadRequestException(
            detail="Must provide either submission_group_id OR (course_content_id + course_member_id)"
        )

    # Check permissions
    can_download = _has_submission_artifact_permission(permissions, ["get", "list"])
    user_id = permissions.get_user_id()
    if user_id and not can_download:
        # Check if user is a member of the submission group
        is_group_member = db.query(SubmissionGroupMember).join(
            CourseMember
        ).filter(
            SubmissionGroupMember.submission_group_id == submission_group.id,
            CourseMember.user_id == user_id
        ).first()

        if not is_group_member:
            # Check for tutor/instructor permissions
            has_elevated_perms = check_course_permissions(
                permissions, CourseMember, "_tutor", db
            ).filter(
                CourseMember.course_id == submission_group.course_id,
                CourseMember.user_id == user_id
            ).first()

            if not has_elevated_perms:
                raise ForbiddenException(detail="You don't have permission to download this submission")
    elif not can_download:
        raise ForbiddenException(detail="You don't have permission to download this submission")

    # Build query for artifacts
    query = db.query(SubmissionArtifact).filter(
        SubmissionArtifact.submission_group_id == submission_group.id
    )

    # Filter by version identifier if provided
    if version_identifier:
        query = query.filter(SubmissionArtifact.version_identifier == version_identifier)

    # Filter by submit flag
    if submit_only:
        query = query.filter(SubmissionArtifact.submit == True)

    # Get the latest artifact
    artifact = query.order_by(
        SubmissionArtifact.uploaded_at.desc()
    ).first()

    if not artifact:
        raise NotFoundException(detail="No submission found matching the criteria")

    # Delegate to business logic layer
    zip_buffer, filename = await download_submission_as_zip(
        artifact_id=str(artifact.id),
        permissions=permissions,
        db=db,
        storage_service=storage_service,
    )

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

@submissions_router.get("/artifacts/{artifact_id}/download")
async def download_submission_artifact(
    artifact_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    storage_service = Depends(get_storage_service),
):
    """Download a specific submission artifact as a ZIP file by artifact ID."""
    from fastapi.responses import StreamingResponse

    # Delegate to business logic layer
    zip_buffer, filename = await download_submission_as_zip(
        artifact_id=artifact_id,
        permissions=permissions,
        db=db,
        storage_service=storage_service,
    )

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

# ===============================
# Artifact Grade Endpoints
# ===============================

@submissions_router.post("/artifacts/{artifact_id}/grades", response_model=SubmissionGradeDetail, status_code=status.HTTP_201_CREATED)
async def create_artifact_grade_endpoint(
    artifact_id: str,
    grade_data: SubmissionGradeCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
):
    """Create a grade for an artifact. Requires instructor/tutor permissions."""

    grade = create_artifact_grade(
        artifact_id=artifact_id,
        grade=grade_data.grade,
        status=grade_data.status.value if hasattr(grade_data.status, 'value') else grade_data.status,
        comment=grade_data.comment,
        permissions=permissions,
        db=db,
        cache=cache,
    )

    return SubmissionGradeDetail.model_validate(grade)

@submissions_router.get("/artifacts/{artifact_id}/grades", response_model=list[SubmissionGradeListItem])
async def list_artifact_grades(
    artifact_id: str,
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """List all grades for an artifact. Students can view their own grades, tutors/instructors can view all."""

    # Verify artifact exists and get submission group
    artifact = db.query(SubmissionArtifact).options(
        joinedload(SubmissionArtifact.submission_group)
    ).filter(
        SubmissionArtifact.id == artifact_id
    ).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Check permissions - students can only see grades for their own submissions
    user_id = permissions.get_user_id()
    if user_id and not permissions.is_admin:
        # Check if user is a member of the submission group or has tutor/instructor permissions
        is_group_member = db.query(SubmissionGroupMember).join(
            CourseMember
        ).filter(
            SubmissionGroupMember.submission_group_id == artifact.submission_group_id,
            CourseMember.user_id == user_id
        ).first()

        if not is_group_member:
            # Check for tutor/instructor permissions
            has_elevated_perms = check_course_permissions(
                permissions, CourseMember, "_tutor", db
            ).filter(
                CourseMember.course_id == artifact.submission_group.course_id,
                CourseMember.user_id == user_id
            ).first()

            if not has_elevated_perms:
                raise ForbiddenException(detail="You don't have permission to view these grades")

    # Get grades for this artifact
    grades = db.query(SubmissionGrade).options(
        joinedload(SubmissionGrade.graded_by)
    ).filter(
        SubmissionGrade.artifact_id == artifact_id
    ).order_by(SubmissionGrade.graded_at.desc()).all()

    response.headers["X-Total-Count"] = str(len(grades))

    return [SubmissionGradeListItem.model_validate(grade) for grade in grades]

@submissions_router.patch("/grades/{grade_id}", response_model=SubmissionGradeDetail)
async def update_artifact_grade(
    grade_id: str,
    update_data: SubmissionGradeUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
):
    """Update an existing grade. Only the grader can update their own grade."""
    from computor_backend.database import set_db_user

    # Set user context for audit tracking
    set_db_user(db, permissions.user_id)

    grade = update_grade(
        grade_id=grade_id,
        grade=update_data.grade,
        status=update_data.status.value if hasattr(update_data.status, 'value') else update_data.status,
        comment=update_data.comment,
        permissions=permissions,
        db=db,
        cache=cache,
    )

    return SubmissionGradeDetail.model_validate(grade)

@submissions_router.delete("/grades/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact_grade(
    grade_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
):
    """Delete a grade. Only the grader or an admin can delete."""
    from computor_backend.database import set_db_user

    # Set user context for audit tracking
    set_db_user(db, permissions.user_id)

    delete_grade(
        grade_id=grade_id,
        permissions=permissions,
        db=db,
        cache=cache,
    )

# ===============================
# Artifact Review Endpoints
# ===============================

@submissions_router.post("/artifacts/{artifact_id}/reviews", response_model=SubmissionReviewListItem, status_code=status.HTTP_201_CREATED)
async def create_artifact_review(
    artifact_id: str,
    review_data: SubmissionReviewCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Create a review for an artifact."""
    from computor_backend.database import set_db_user

    # Set user context for audit tracking
    set_db_user(db, permissions.user_id)

    # Get the artifact
    artifact = db.query(SubmissionArtifact).options(
        joinedload(SubmissionArtifact.submission_group)
    ).filter(SubmissionArtifact.id == artifact_id).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Check if user is a course member (any role can review)
    course = artifact.submission_group.course
    principal_user_id = permissions.get_user_id()

    # Use check_course_permissions to find the course member (works for any role)
    course_member = check_course_permissions(
        permissions, CourseMember, "_student", db  # _student is the minimum role
    ).filter(
        CourseMember.course_id == course.id,
        CourseMember.user_id == principal_user_id
    ).first()

    if not course_member:
        raise ForbiddenException(detail="You must be a course member to review artifacts")

    # Create the review (use authenticated user's course member id)
    review = SubmissionReview(
        artifact_id=artifact_id,
        reviewer_course_member_id=course_member.id,  # Use the authenticated reviewer's member ID
        body=review_data.body,
        review_type=review_data.review_type,
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    logger.info(f"Created review {review.id} for artifact {artifact_id}")

    return SubmissionReviewListItem.model_validate(review)

@submissions_router.get("/artifacts/{artifact_id}/reviews", response_model=list[SubmissionReviewListItem])
async def list_artifact_reviews(
    artifact_id: str,
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """List all reviews for an artifact. Any course member can view reviews."""

    # Verify artifact exists and get course info
    artifact = db.query(SubmissionArtifact).options(
        joinedload(SubmissionArtifact.submission_group)
    ).filter(
        SubmissionArtifact.id == artifact_id
    ).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Check if user is a course member (any role can view reviews)
    user_id = permissions.get_user_id()
    if user_id and not permissions.is_admin:
        is_course_member = check_course_permissions(
            permissions, CourseMember, "_student", db  # _student is minimum role
        ).filter(
            CourseMember.course_id == artifact.submission_group.course_id,
            CourseMember.user_id == user_id
        ).first()

        if not is_course_member:
            raise ForbiddenException(detail="You must be a course member to view reviews")

    # Get reviews for this artifact
    reviews = db.query(SubmissionReview).options(
        joinedload(SubmissionReview.reviewer)
    ).filter(
        SubmissionReview.artifact_id == artifact_id
    ).order_by(SubmissionReview.created_at.desc()).all()

    response.headers["X-Total-Count"] = str(len(reviews))

    return [SubmissionReviewListItem.model_validate(review) for review in reviews]

@submissions_router.patch("/reviews/{review_id}", response_model=SubmissionReviewListItem)
async def update_artifact_review(
    review_id: str,
    update_data: SubmissionReviewUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Update an existing review. Only the reviewer can update their own review."""
    from computor_backend.database import set_db_user

    # Set user context for audit tracking
    set_db_user(db, permissions.user_id)

    review = db.query(SubmissionReview).options(
        joinedload(SubmissionReview.reviewer)
    ).filter(SubmissionReview.id == review_id).first()

    if not review:
        raise NotFoundException(detail="Review not found")

    # Check if user is the reviewer
    principal_user_id = permissions.get_user_id()
    if str(review.reviewer.user_id) != str(principal_user_id):
        raise ForbiddenException(detail="You can only update your own reviews")

    # Update fields
    if update_data.body is not None:
        review.body = update_data.body
    if update_data.review_type is not None:
        review.review_type = update_data.review_type

    db.commit()
    db.refresh(review)

    return SubmissionReviewListItem.model_validate(review)

@submissions_router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact_review(
    review_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Delete a review. Only the reviewer or an admin can delete."""
    from computor_backend.database import set_db_user

    # Set user context for audit tracking
    set_db_user(db, permissions.user_id)

    review = db.query(SubmissionReview).filter(SubmissionReview.id == review_id).first()

    if not review:
        raise NotFoundException(detail="Review not found")

    # Check permissions
    principal_user_id = permissions.get_user_id()
    if str(review.reviewer.user_id) != str(principal_user_id):
        # Check if user is instructor (higher permission needed to delete others' reviews)
        course = review.artifact.submission_group.course
        is_instructor = check_course_permissions(
            permissions, CourseMember, "_lecturer", db  # Use _lecturer for instructor role
        ).filter(
            CourseMember.course_id == course.id,
            CourseMember.user_id == principal_user_id
        ).first()

        if not is_instructor:
            raise ForbiddenException(detail="Only instructors can delete other people's reviews")

    db.delete(review)
    db.commit()

    logger.info(f"Deleted review {review_id}")

# ===============================
# Test Result Endpoints
# ===============================

@submissions_router.post("/artifacts/{artifact_id}/test", response_model=ResultList, status_code=status.HTTP_201_CREATED)
async def create_test_result(
    artifact_id: str,
    test_data: ResultCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Create a test result for an artifact. Checks for test limitations."""
    from computor_backend.database import set_db_user

    # Set user context for audit tracking
    set_db_user(db, permissions.user_id)

    # Get the artifact
    artifact = db.query(SubmissionArtifact).options(
        joinedload(SubmissionArtifact.submission_group)
    ).filter(SubmissionArtifact.id == artifact_id).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Check if user has permission to run tests (students can test their own, tutors/instructors can test any)
    principal_user_id = permissions.get_user_id()
    course = artifact.submission_group.course

    # First check if user is a course member at all
    course_member = check_course_permissions(
        permissions, CourseMember, "_student", db
    ).filter(
        CourseMember.course_id == course.id,
        CourseMember.user_id == principal_user_id
    ).first()

    if not course_member:
        raise ForbiddenException(detail="You must be a course member to run tests")

    # Check if student is testing their own submission
    is_own_submission = db.query(SubmissionGroupMember).filter(
        SubmissionGroupMember.submission_group_id == artifact.submission_group_id,
        SubmissionGroupMember.course_member_id == course_member.id
    ).first()

    if not is_own_submission:
        # If not their own submission, they need tutor or higher permissions
        has_test_permission = check_course_permissions(
            permissions, CourseMember, "_tutor", db
        ).filter(
            CourseMember.course_id == course.id,
            CourseMember.user_id == principal_user_id
        ).first()

        if not has_test_permission:
            raise ForbiddenException(detail="Students can only test their own submissions")

    # Check test limitations (prevent multiple successful tests by same member)
    existing_test = db.query(Result).filter(
        and_(
            Result.submission_artifact_id == artifact_id,
            Result.course_member_id == test_data.course_member_id,
            ~Result.status.in_([1, 2, 6])  # Not failed, cancelled, or crashed
        )
    ).first()

    if existing_test:
        raise BadRequestException(
            detail="You have already run a test on this artifact. "
                   "Multiple tests are not allowed unless the previous test crashed or was cancelled."
        )

    # Check max test runs limit if configured
    submission_group = artifact.submission_group
    if submission_group.max_test_runs is not None:
        test_count = db.query(Result).filter(
            Result.submission_artifact_id == artifact_id
        ).count()

        if test_count >= submission_group.max_test_runs:
            raise BadRequestException(
                detail=f"Maximum test runs ({submission_group.max_test_runs}) reached for this artifact"
            )

    # Create the test result (use authenticated user's course member id)
    from computor_types.tasks import map_task_status_to_int
    from computor_backend.services.result_storage import store_result_json

    # Extract result_json to store separately
    result_json_data = test_data.result_json

    result = Result(
        submission_artifact_id=artifact_id,
        course_member_id=course_member.id,  # Use authenticated user's course member ID
        testing_service_id=test_data.testing_service_id,
        test_system_id=test_data.test_system_id,
        status=map_task_status_to_int(test_data.status),
        grade=test_data.grade,
        properties=test_data.properties,
        version_identifier=test_data.version_identifier,
        reference_version_identifier=test_data.reference_version_identifier,
    )

    db.add(result)
    db.commit()
    db.refresh(result)

    # Store result_json in MinIO if provided
    if result_json_data is not None:
        await store_result_json(result.id, result_json_data)

    logger.info(f"Created result {result.id} for artifact {artifact_id}")

    return ResultList.model_validate(result)

@submissions_router.get("/artifacts/{artifact_id}/tests", response_model=list[ResultGet])
async def list_artifact_test_results(
    artifact_id: str,
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    include_failed: Annotated[bool, Query(description="Include failed/cancelled/crashed results")] = False,
):
    """List test results for an artifact. By default only successful results (status=0) are returned.

    Use include_failed=true to also include failed/cancelled/crashed results.
    Students see their own, tutors/instructors see all.
    """
    from computor_backend.services.result_storage import retrieve_result_json, list_result_artifacts

    # Verify artifact exists and get course info
    artifact = db.query(SubmissionArtifact).options(
        joinedload(SubmissionArtifact.submission_group)
    ).filter(
        SubmissionArtifact.id == artifact_id
    ).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Check permissions
    user_id = permissions.get_user_id()
    if user_id and not permissions.is_admin:
        # Check if user is a member of the submission group
        is_group_member = db.query(SubmissionGroupMember).join(
            CourseMember
        ).filter(
            SubmissionGroupMember.submission_group_id == artifact.submission_group_id,
            CourseMember.user_id == user_id
        ).first()

        if not is_group_member:
            # If not in the group, check for tutor/instructor permissions
            has_elevated_perms = check_course_permissions(
                permissions, CourseMember, "_tutor", db
            ).filter(
                CourseMember.course_id == artifact.submission_group.course_id,
                CourseMember.user_id == user_id
            ).first()

            if not has_elevated_perms:
                raise ForbiddenException(detail="You can only view test results for your own submissions")

    # Build query for test results
    query = db.query(Result).filter(Result.submission_artifact_id == artifact_id)

    # By default, only return successful results (status=0)
    # Failed=1, Cancelled=2, Crashed=6
    if not include_failed:
        query = query.filter(Result.status == 0)

    results = query.order_by(Result.created_at.desc()).all()

    response.headers["X-Total-Count"] = str(len(results))

    # Build ResultGet responses with full details
    result_list = []
    for result in results:
        # Fetch result_json and artifacts from MinIO
        result_json_data = await retrieve_result_json(result.id)
        artifacts = await list_result_artifacts(result.id)

        result_artifacts = [
            ResultArtifactInfo(
                id=f"{result.id}_{artifact['filename']}",
                filename=artifact['filename'],
                content_type=artifact.get('content_type'),
                file_size=artifact['size'],
                created_at=artifact['last_modified'].isoformat() if artifact.get('last_modified') else None,
            )
            for artifact in artifacts
        ]

        result_get = ResultGet(
            id=str(result.id),
            created_at=result.created_at,
            updated_at=result.updated_at,
            course_member_id=str(result.course_member_id),
            submission_artifact_id=str(result.submission_artifact_id) if result.submission_artifact_id else None,
            submission_group_id=str(result.submission_group_id) if result.submission_group_id else None,
            course_content_id=str(result.course_content_id),
            course_content_type_id=str(result.course_content_type_id),
            testing_service_id=str(result.testing_service_id) if result.testing_service_id else None,
            test_system_id=result.test_system_id,
            grade=result.grade,
            result=result.result,
            result_json=result_json_data,
            started_at=result.started_at,
            finished_at=result.finished_at,
            version_identifier=result.version_identifier,
            reference_version_identifier=result.reference_version_identifier,
            status=result.status,
            properties=result.properties,
            has_artifacts=len(artifacts) > 0,
            artifact_count=len(artifacts),
            result_artifacts=result_artifacts,
        )
        result_list.append(result_get)

    return result_list

@submissions_router.patch("/tests/{test_id}", response_model=ResultList)
async def update_test_result(
    test_id: str,
    update_data: ResultUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
):
    """Update a test result (e.g., when test completes). Only the test runner or admin can update."""

    # Initialize repository with cache for automatic invalidation
    result_repo = ResultRepository(db, cache)

    result = db.query(Result).filter(Result.id == test_id).first()

    if not result:
        raise NotFoundException(detail="Test result not found")

    # Check permissions - either admin (service account) or the test runner
    user_id = permissions.get_user_id()
    is_admin = permissions.has_claim("_admin")

    if not is_admin:
        # Check if user is the one who ran the test
        course_member = db.query(CourseMember).filter(
            CourseMember.id == result.course_member_id
        ).first()

        if not course_member or str(course_member.user_id) != str(user_id):
            raise ForbiddenException(detail="Only the test runner or admin can update test results")

    # Build updates dict
    from computor_backend.services.result_storage import store_result_json

    updates = {}
    result_json_update = None

    if update_data.status is not None:
        from computor_types.tasks import map_task_status_to_int
        updates['status'] = map_task_status_to_int(update_data.status)
    if update_data.grade is not None:
        updates['grade'] = update_data.grade
    if update_data.result_json is not None:
        # Handle result_json separately - store in MinIO
        result_json_update = update_data.result_json
    if update_data.properties is not None:
        updates['properties'] = update_data.properties
    if update_data.finished_at is not None:
        updates['finished_at'] = update_data.finished_at

    # Store result_json in MinIO if provided
    if result_json_update is not None:
        await store_result_json(test_id, result_json_update)

    # CRITICAL: Use repository.update() for automatic cache invalidation
    if updates:
        result = result_repo.update(str(test_id), updates)

    logger.info("Updated test result %s (cache invalidated)", test_id)

    return ResultList.model_validate(result)
