"""API endpoints for submission artifacts, grading and reviews."""
import io
import logging
import zipfile
from datetime import datetime
from pathlib import PurePosixPath
from typing import Annotated, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Response, status, File, Form, UploadFile, Request
from sqlalchemy.orm import Session, joinedload, contains_eager, aliased
from sqlalchemy import and_, or_, exists, func as sql_func

from computor_backend.api._pagination import paginated_list
from computor_backend.exceptions import (
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
from computor_backend.permissions.roles import TUTOR_AND_ABOVE
from computor_types.artifacts import (
    SubmissionArtifactList,
    SubmissionArtifactGet,
    SubmissionArtifactUpdate,
    SubmissionArtifactQuery,
    SubmissionGradeCreate,
    SubmissionGradeUpdate,
    SubmissionGradeList,
    SubmissionGradeDetail,
    SubmissionGradeQuery,
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

    return paginated_list(result_list, total, response=response)

@submissions_router.get(
    "/artifacts/download",
    responses={200: {"content": {"application/zip": {}}}},
)
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

    artifact = update_artifact(
        artifact_id=artifact_id,
        submit=update_data.submit,
        properties=update_data.properties,
        permissions=permissions,
        db=db,
        cache=cache,
    )

    return get_artifact_with_details(artifact)

@submissions_router.get(
    "/artifacts/{artifact_id}/download",
    responses={200: {"content": {"application/zip": {}}}},
)
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

@submissions_router.get("/artifacts/{artifact_id}/grades", response_model=list[SubmissionGradeList])
async def list_artifact_grades(
    artifact_id: str,
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: SubmissionGradeQuery = Depends(),
    db: Session = Depends(get_db),
):
    """List all grades for an artifact. Students can view their own grades, tutors/instructors can view all.

    Query parameters:
    - graded_by_course_member_id: Filter by grader
    - status: Filter by grading status
    - latest: If True, return only the most recent grade
    - start_date: Filter grades at or after this datetime
    - end_date: Filter grades at or before this datetime
    """

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

    # Build query for grades
    query = db.query(SubmissionGrade).options(
        joinedload(SubmissionGrade.graded_by)
    ).filter(
        SubmissionGrade.artifact_id == artifact_id
    )

    # Apply query filters
    if params.graded_by_course_member_id:
        query = query.filter(SubmissionGrade.graded_by_course_member_id == params.graded_by_course_member_id)
    if params.status is not None:
        query = query.filter(SubmissionGrade.status == params.status)
    if params.start_date:
        query = query.filter(SubmissionGrade.graded_at >= params.start_date)
    if params.end_date:
        query = query.filter(SubmissionGrade.graded_at <= params.end_date)

    # Order by graded_at descending
    query = query.order_by(SubmissionGrade.graded_at.desc())

    # If latest=True, only return the most recent grade
    if params.latest:
        grade = query.first()
        grades = [grade] if grade else []
        total = len(grades)
    else:
        total = query.count()
        grades = query.limit(params.limit).offset(params.skip).all()

    return paginated_list(grades, total, response=response, schema=SubmissionGradeList)

@submissions_router.get("/grades", response_model=list[SubmissionGradeList])
async def list_grades(
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: SubmissionGradeQuery = Depends(),
    db: Session = Depends(get_db),
):
    """List submission grades with filtering.

    Query parameters:
    - artifact_id: Filter by specific artifact
    - graded_by_course_member_id: Filter by grader
    - status: Filter by grading status
    - course_id: Filter by course
    - latest: If True, return only the most recent grade per artifact
    - start_date: Filter grades at or after this datetime
    - end_date: Filter grades at or before this datetime
    """

    can_list_all = permissions.is_admin or permissions.permitted("submission_grade", "list")
    user_id = permissions.get_user_id()

    # Determine if we need to join artifact/submission_group for filtering
    needs_artifact_join = params.course_id or (user_id and not can_list_all)

    # Build base query with explicit joins when needed for filtering
    if needs_artifact_join:
        # Use explicit joins with contains_eager to populate relationships
        query = db.query(SubmissionGrade).join(
            SubmissionArtifact, SubmissionGrade.artifact_id == SubmissionArtifact.id
        ).join(
            SubmissionGroup, SubmissionArtifact.submission_group_id == SubmissionGroup.id
        ).options(
            joinedload(SubmissionGrade.graded_by),
            contains_eager(SubmissionGrade.artifact).contains_eager(SubmissionArtifact.submission_group)
        )
    else:
        # No filtering needs - use simple joinedload
        query = db.query(SubmissionGrade).options(
            joinedload(SubmissionGrade.graded_by),
            joinedload(SubmissionGrade.artifact).joinedload(SubmissionArtifact.submission_group)
        )

    # Apply basic filters
    if params.id:
        query = query.filter(SubmissionGrade.id == params.id)
    if params.artifact_id:
        query = query.filter(SubmissionGrade.artifact_id == params.artifact_id)
    if params.graded_by_course_member_id:
        query = query.filter(SubmissionGrade.graded_by_course_member_id == params.graded_by_course_member_id)
    if params.status is not None:
        query = query.filter(SubmissionGrade.status == params.status)
    if params.start_date:
        query = query.filter(SubmissionGrade.graded_at >= params.start_date)
    if params.end_date:
        query = query.filter(SubmissionGrade.graded_at <= params.end_date)

    # Filter by course_id (join already done above if needed)
    if params.course_id:
        query = query.filter(SubmissionGroup.course_id == params.course_id)

    # Permission-based filtering using EXISTS (more efficient than IN with subqueries)
    if user_id and not can_list_all:
        # Create aliased tables for EXISTS subqueries to avoid conflicts
        ArtifactAlias = aliased(SubmissionArtifact)
        GroupMemberAlias = aliased(SubmissionGroupMember)
        CourseMemberAlias = aliased(CourseMember)

        # EXISTS: user is member of the submission group (owns the submission)
        own_submission_exists = exists().where(
            and_(
                ArtifactAlias.id == SubmissionGrade.artifact_id,
                GroupMemberAlias.submission_group_id == ArtifactAlias.submission_group_id,
                CourseMemberAlias.id == GroupMemberAlias.course_member_id,
                CourseMemberAlias.user_id == user_id
            )
        )

        # EXISTS: user created this grade
        GraderAlias = aliased(CourseMember)
        own_grade_exists = exists().where(
            and_(
                GraderAlias.id == SubmissionGrade.graded_by_course_member_id,
                GraderAlias.user_id == user_id
            )
        )

        # EXISTS: user is tutor/instructor in the course
        TutorAlias = aliased(CourseMember)
        tutor_exists = exists().where(
            and_(
                TutorAlias.course_id == SubmissionGroup.course_id,
                TutorAlias.user_id == user_id,
                TutorAlias.course_role_id.in_(TUTOR_AND_ABOVE)
            )
        )

        # Combine with OR
        query = query.filter(or_(own_submission_exists, own_grade_exists, tutor_exists))

    # If latest=True, filter to only the most recent grade per artifact
    if params.latest:
        # Subquery to find max graded_at per artifact
        latest_subquery = db.query(
            SubmissionGrade.artifact_id,
            sql_func.max(SubmissionGrade.graded_at).label('max_graded_at')
        ).group_by(SubmissionGrade.artifact_id).subquery()

        # Filter main query to only grades matching the max timestamp
        query = query.filter(
            and_(
                SubmissionGrade.artifact_id == latest_subquery.c.artifact_id,
                SubmissionGrade.graded_at == latest_subquery.c.max_graded_at
            )
        )

    # Order by graded_at descending
    query = query.order_by(SubmissionGrade.graded_at.desc())

    # Get total count before pagination
    total = query.count()

    # Apply pagination
    grades = query.limit(params.limit).offset(params.skip).all()

    return paginated_list(grades, total, response=response, schema=SubmissionGradeList)


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
async def create_artifact_review_endpoint(
    artifact_id: str,
    review_data: SubmissionReviewCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Create a review for an artifact."""
    from computor_backend.database import set_db_user

    # Set user context for audit tracking
    set_db_user(db, permissions.user_id)

    review = create_artifact_review(
        artifact_id=artifact_id,
        body=review_data.body,
        review_type=review_data.review_type,
        permissions=permissions,
        db=db,
    )

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

    return paginated_list(reviews, len(reviews), response=response, schema=SubmissionReviewListItem)

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

    review = update_review(
        review_id=review_id,
        body=update_data.body,
        review_type=update_data.review_type,
        permissions=permissions,
        db=db,
    )

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

    delete_review(
        review_id=review_id,
        permissions=permissions,
        db=db,
    )

# ===============================
# Test Result Endpoints
# ===============================

@submissions_router.post("/artifacts/{artifact_id}/test", response_model=ResultList, status_code=status.HTTP_201_CREATED)
async def create_test_result_endpoint(
    artifact_id: str,
    test_data: ResultCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Create a test result for an artifact. Checks for test limitations."""
    from computor_backend.database import set_db_user

    # Set user context for audit tracking
    set_db_user(db, permissions.user_id)

    result = await create_test_result(
        artifact_id=artifact_id,
        course_member_id=test_data.course_member_id,
        testing_service_id=test_data.testing_service_id,
        test_system_id=test_data.test_system_id,
        status=test_data.status,
        grade=test_data.grade,
        result_json=test_data.result_json,
        properties=test_data.properties,
        version_identifier=test_data.version_identifier,
        reference_version_identifier=test_data.reference_version_identifier,
        permissions=permissions,
        db=db,
    )

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

    return paginated_list(result_list, len(result_list), response=response)

@submissions_router.patch("/tests/{test_id}", response_model=ResultList)
async def update_test_result_endpoint(
    test_id: str,
    update_data: ResultUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
):
    """Update a test result (e.g., when test completes). Only the test runner or admin can update."""

    result = await update_test_result(
        test_id=test_id,
        status=update_data.status,
        grade=update_data.grade,
        result_json=update_data.result_json,
        properties=update_data.properties,
        finished_at=update_data.finished_at,
        permissions=permissions,
        db=db,
        cache=cache,
    )

    return ResultList.model_validate(result)
