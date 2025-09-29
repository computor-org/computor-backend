import io
import logging
import mimetypes
import re
import zipfile
from datetime import datetime
from pathlib import PurePosixPath
from typing import Annotated, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ctutor_backend.api.crud import list_db
from ctutor_backend.api.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from ctutor_backend.database import get_db
from ctutor_backend.interface.tasks import TaskStatus, map_task_status_to_int
from ctutor_backend.model.course import (
    CourseContent,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)
from ctutor_backend.model.artifact import SubmissionArtifact
from ctutor_backend.model.result import Result
from ctutor_backend.permissions.auth import get_current_permissions
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.services.storage_service import get_storage_service
from ctutor_backend.storage_security import perform_full_file_validation, sanitize_filename
from ctutor_backend.storage_config import MAX_UPLOAD_SIZE, format_bytes
from ctutor_backend.interface.submissions import (
    SubmissionCreate,
    SubmissionInterface,
    SubmissionListItem,
    SubmissionQuery,
    SubmissionUploadResponseModel,
    SubmissionUploadedFile,
)
from ctutor_backend.interface.artifacts import SubmissionArtifactInterface

logger = logging.getLogger(__name__)

submissions_router = APIRouter(prefix="/submissions", tags=["submissions"])
_DIR_ALLOWED_PATTERN = re.compile(r"[^A-Za-z0-9_.-]")


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


@submissions_router.get("", response_model=list)
async def list_submissions(
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    params = Depends(),
    db: Session = Depends(get_db),
):
    """List submission artifacts with optional filtering."""

    submissions, total = await list_db(permissions, db, params, SubmissionArtifactInterface)
    response.headers["X-Total-Count"] = str(total)
    return submissions


@submissions_router.post("", response_model=SubmissionUploadResponseModel, status_code=status.HTTP_201_CREATED)
async def upload_submission(
    submission_create: Annotated[str, Form(..., description="Submission metadata as JSON")],
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    response: Response,
    file: UploadFile = File(..., description="Submission ZIP archive"),
    db: Session = Depends(get_db),
    storage_service = Depends(get_storage_service),
):
    """Upload a submission file to MinIO and create a matching Result record."""

    try:
        submission_data = SubmissionCreate.model_validate_json(submission_create)
    except ValidationError as validation_error:
        raise BadRequestException(detail=f"Invalid submission metadata: {validation_error}") from validation_error

    # Resolve submission group with permission check
    submission_group = (
        check_course_permissions(permissions, SubmissionGroup, "_student", db)
        .options(
            joinedload(SubmissionGroup.course_content),
            joinedload(SubmissionGroup.members).joinedload(SubmissionGroupMember.course_member),
        )
        .filter(SubmissionGroup.id == submission_data.submission_group_id)
        .first()
    )

    if not submission_group:
        raise NotFoundException(detail="Submission group not found or access denied")

    course_content: CourseContent = submission_group.course_content

    if not course_content:
        raise NotFoundException(detail="Course content not found for submission group")

    if not course_content.is_submittable:
        raise BadRequestException(detail="This course content does not accept submissions")

    if not course_content.execution_backend_id:
        raise BadRequestException(detail="Course content is missing an execution backend to link submissions")

    # Determine submitting course member
    submitting_member: Optional[CourseMember] = None
    principal_user_id = permissions.get_user_id()

    if not submission_group.members:
        raise BadRequestException(detail="Submission group does not have any members")

    if principal_user_id:
        membership = next(
            (
                member_assoc
                for member_assoc in submission_group.members
                if member_assoc.course_member and str(member_assoc.course_member.user_id) == str(principal_user_id)
            ),
            None,
        )
        if membership:
            submitting_member = membership.course_member

    if not submitting_member:
        if len(submission_group.members) == 1:
            submitting_member = submission_group.members[0].course_member
        else:
            raise ForbiddenException(detail="Unable to resolve submitting course member for this group")

    if not submitting_member:
        raise NotFoundException(detail="Submitting course member could not be resolved")

    trimmed_version = (submission_data.version_identifier or "").strip() or None
    if trimmed_version and len(trimmed_version) > 2048:
        raise BadRequestException(detail="version_identifier exceeds maximum length of 2048 characters")

    manual_version_identifier = trimmed_version or f"manual-{uuid4()}"

    # Check submission quota limits (if configured)
    if submission_group.max_submissions is not None:
        submitted_count = (
            db.query(func.count(SubmissionArtifact.id))
            .filter(SubmissionArtifact.submission_group_id == submission_group.id)
            .scalar()
        )
        if submitted_count >= submission_group.max_submissions:
            raise BadRequestException(detail="Submission limit reached for this group")

    # Read file for validation and unzip for storage
    file_content = await file.read()
    file_size = len(file_content)
    file_data = io.BytesIO(file_content)

    perform_full_file_validation(
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        file_data=file_data,
    )

    archive_suffix = PurePosixPath(file.filename or "").suffix.lower()
    if archive_suffix != ".zip":
        raise BadRequestException("Only ZIP archives are supported for submissions")

    timestamp_prefix = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
    submission_prefix = f"submission-{timestamp_prefix}-{uuid4().hex}"
    bucket_name = str(submission_group.id).lower()
    created_artifacts: List[UUID] = []
    total_uploaded_size = 0

    file_data.seek(0)
    try:
        with zipfile.ZipFile(file_data) as archive:
            members = [info for info in archive.infolist() if not info.is_dir()]
            if not members:
                raise BadRequestException("Archive does not contain any files")

            total_unpacked_size = sum(info.file_size for info in members)
            if total_unpacked_size == 0:
                raise BadRequestException("Archive contains only empty files")
            if total_unpacked_size > MAX_UPLOAD_SIZE:
                raise BadRequestException(
                    f"Extracted content exceeds maximum allowed size of {format_bytes(MAX_UPLOAD_SIZE)}"
                )

            storage_meta_base: dict[str, str] = {
                "submission_group_id": str(submission_group.id),
                "course_content_id": str(course_content.id),
                "course_member_id": str(submitting_member.id),
                "archive_filename": file.filename or "submission.zip",
                "manual_submission": "true",
                "submission_prefix": submission_prefix,
                "submission_version": manual_version_identifier,
            }

            for member in members:
                relative_path = _sanitize_archive_path(member.filename)
                member_size = member.file_size
                if member_size > MAX_UPLOAD_SIZE:
                    raise BadRequestException(
                        f"Archive entry '{member.filename}' exceeds maximum allowed size of {format_bytes(MAX_UPLOAD_SIZE)}"
                    )

                with archive.open(member, "r") as source:
                    extracted_bytes = source.read()

                extracted_stream = io.BytesIO(extracted_bytes)
                content_type = (
                    mimetypes.guess_type(relative_path)[0]
                    or "application/octet-stream"
                )

                object_key = f"{submission_prefix}/{relative_path}"
                per_file_metadata = {
                    key: str(value)
                    for key, value in (
                        storage_meta_base
                        | {
                            "relative_path": relative_path,
                            "file_size": str(member_size),
                        }
                    ).items()
                }

                extracted_stream.seek(0)
                stored = await storage_service.upload_file(
                    file_data=extracted_stream,
                    object_key=object_key,
                    bucket_name=bucket_name,
                    content_type=content_type,
                    metadata=per_file_metadata,
                )

                # Create SubmissionArtifact record
                artifact = SubmissionArtifact(
                    submission_group_id=submission_group.id,
                    uploaded_by_course_member_id=submitting_member.id,
                    filename=relative_path,
                    original_filename=member.filename,
                    content_type=stored.content_type,
                    file_size=stored.size,
                    bucket_name=bucket_name,
                    object_key=object_key,
                    properties={
                        "version_identifier": manual_version_identifier,
                        "submission_prefix": submission_prefix,
                        "archive_filename": file.filename or "submission.zip",
                        "manual_submission": True,
                    }
                )

                db.add(artifact)
                db.flush()  # Get the ID without committing
                created_artifacts.append(artifact.id)
                total_uploaded_size += stored.size

    except zipfile.BadZipFile as exc:
        raise BadRequestException("Uploaded file is not a valid ZIP archive") from exc

    if not created_artifacts:
        raise BadRequestException("Failed to extract any files from the archive")

    # Commit all artifacts
    db.commit()

    logger.info(
        "Created %d submission artifacts for group %s", len(created_artifacts), submission_group.id
    )

    return SubmissionUploadResponseModel(
        artifacts=created_artifacts,
        submission_group_id=submission_group.id,
        uploaded_by_course_member_id=submitting_member.id,
        total_size=total_uploaded_size,
        files_count=len(created_artifacts),
        uploaded_at=datetime.utcnow(),
        version_identifier=manual_version_identifier,
    )
