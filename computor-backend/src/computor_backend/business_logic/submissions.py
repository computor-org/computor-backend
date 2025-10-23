"""Business logic for submission management."""
import io
import logging
import mimetypes
import re
import zipfile
from datetime import datetime
from pathlib import PurePosixPath
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload
from starlette.concurrency import run_in_threadpool

from computor_backend.api.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
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
from computor_backend.permissions.core import check_course_permissions
from computor_backend.cache import Cache
from computor_backend.repositories.submission_artifact import SubmissionArtifactRepository
from computor_backend.permissions.principal import Principal
from computor_backend.services.storage_service import StorageService
from computor_backend.storage_security import perform_full_file_validation, sanitize_filename
from computor_backend.storage_config import MAX_UPLOAD_SIZE, format_bytes
from computor_types.artifacts import SubmissionArtifactGet
from computor_types.submissions import SubmissionUploadResponseModel

logger = logging.getLogger(__name__)

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


def _should_skip_file(filename: str) -> bool:
    """
    Determine if a file should be skipped during submission extraction.

    Skips:
    - Executable and binary files (.exe, .bin, .dll, .so, .dylib, etc.)
    - Dangerous file types (.bat, .cmd, .sh, .ps1, etc.)
    - macOS system files (.DS_Store, __MACOSX/)
    - Windows system files (Thumbs.db, desktop.ini)
    - Version control files (.git/, .gitignore, .gitattributes, .svn/)
    - IDE files (.idea/, .vscode/)
    - Build artifacts (node_modules/, __pycache__/)
    - Documentation files (README.md, README_*.md)
    - Media directories (mediaFiles/, media/)
    - Hidden files starting with . (except .gitignore is explicitly skipped)
    """
    filename_lower = filename.lower()
    path_parts = filename.split('/')

    # Get the base filename (last part of path)
    base_filename = path_parts[-1] if path_parts else filename

    # Get file extension (including the dot)
    file_ext = ''
    if '.' in base_filename:
        file_ext = base_filename[base_filename.rfind('.'):].lower()

    # Skip dangerous executable and binary file extensions
    dangerous_extensions = {
        # Windows executables
        '.exe', '.dll', '.com', '.bat', '.cmd', '.msi', '.scr', '.vbs', '.wsf',
        # Linux/Unix executables and libraries
        '.bin', '.so', '.a', '.o',
        # macOS executables and libraries
        '.dylib', '.app', '.dmg', '.pkg',
        # Scripts (potentially dangerous)
        '.ps1', '.psm1',  # PowerShell scripts
        # Compiled Java
        '.class',  # Compiled Java class files (but allow .jar for libraries)
        # Native code
        '.elf',
        # Database files (often binary, large)
        '.db', '.sqlite', '.sqlite3',
        # Disk images
        '.iso', '.img', '.vhd', '.vmdk',
    }

    if file_ext in dangerous_extensions:
        logger.warning(f"Skipping dangerous file extension: {filename} ({file_ext})")
        return True

    # Skip README files (README.md, README_*.md, readme.txt, etc.)
    if base_filename.lower().startswith('readme'):
        return True

    # Skip mediaFiles directory and its contents
    if 'mediafiles' in filename_lower or 'media' in path_parts:
        return True

    # Skip version control files
    version_control_files = {'.gitignore', '.gitattributes', '.gitmodules', '.git'}
    if any(part in version_control_files for part in path_parts):
        return True
    if base_filename.lower() in {'.gitignore', '.gitattributes', '.gitmodules'}:
        return True

    # Skip hidden files and directories (starting with .) except some wanted files
    # Allow: None currently, but structure is here for future additions
    wanted_hidden_files = set()  # Example: {'.env.example', '.editorconfig'}
    if any(part.startswith('.') and part not in wanted_hidden_files for part in path_parts):
        return True

    # Skip macOS system files
    if '.ds_store' in filename_lower or '__macosx' in filename_lower:
        return True

    # Skip Windows system files
    if 'thumbs.db' in filename_lower or 'desktop.ini' in filename_lower:
        return True

    # Skip common build/cache directories
    skip_dirs = {
        'node_modules', '__pycache__', '.pytest_cache', '.mypy_cache',
        'build', 'dist', 'target', 'bin', 'obj', '.gradle', '.next',
        'coverage', '.nyc_output', 'out'
    }
    if any(skip_dir in path_parts for skip_dir in skip_dirs):
        return True

    # Skip backup files
    if filename.endswith('~') or filename.endswith('.bak'):
        return True

    # Skip editor swap/temp files
    if base_filename.endswith('.swp') or base_filename.endswith('.swo'):
        return True
    if base_filename.startswith('.~') or base_filename.endswith('.tmp'):
        return True

    return False


async def upload_submission_artifact(
    submission_group_id: UUID | str,
    file_content: bytes,
    filename: str,
    content_type: str,
    version_identifier: Optional[str],
    submit: bool,
    permissions: Principal,
    db: Session,
    storage_service: StorageService,
    cache: Optional[Cache] = None,
) -> SubmissionUploadResponseModel:
    """Upload a submission file and create artifact record."""

    # Resolve submission group with permission check
    submission_group = (
        check_course_permissions(permissions, SubmissionGroup, "_student", db)
        .options(
            joinedload(SubmissionGroup.course_content),
            joinedload(SubmissionGroup.members).joinedload(SubmissionGroupMember.course_member),
        )
        .filter(SubmissionGroup.id == submission_group_id)
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

    trimmed_version = (version_identifier or "").strip() or None
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
    file_size = len(file_content)
    file_data = io.BytesIO(file_content)

    perform_full_file_validation(
        filename=filename,
        content_type=content_type or "application/octet-stream",
        file_size=file_size,
        file_data=file_data,
    )

    archive_suffix = PurePosixPath(filename or "").suffix.lower()
    if archive_suffix != ".zip":
        raise BadRequestException("Only ZIP archives are supported for submissions")

    # Validate and filter ZIP file content, then upload individual files
    file_data.seek(0)
    try:
        files_included = []
        total_filtered_size = 0

        with zipfile.ZipFile(file_data, 'r') as source_archive:
            members = [info for info in source_archive.infolist() if not info.is_dir()]
            if not members:
                raise BadRequestException("Archive does not contain any files")

            total_unpacked_size = sum(info.file_size for info in members)
            if total_unpacked_size == 0:
                raise BadRequestException("Archive contains only empty files")
            if total_unpacked_size > MAX_UPLOAD_SIZE:
                raise BadRequestException(
                    f"Extracted content exceeds maximum allowed size of {format_bytes(MAX_UPLOAD_SIZE)}"
                )

            # Detect and strip common root directory if all files are under it
            common_root = None
            if members:
                # Get the first path component of each file
                first_components = []
                for member in members:
                    parts = member.filename.split('/')
                    if len(parts) > 1:  # Has at least one directory
                        first_components.append(parts[0])

                # Check if all files share the same first component
                if first_components and len(set(first_components)) == 1 and len(first_components) == len(members):
                    # All files are under the same root directory
                    common_root = first_components[0]
                    logger.debug(f"Detected common root directory: {common_root}")

            # Extract, filter, and upload each file individually to MinIO
            # Use single "submissions" bucket with structure: {group_id}/{version}/{file_path}
            bucket_name = "submissions"

            for member in members:
                # Strip common root directory if detected
                actual_filename = member.filename
                if common_root and actual_filename.startswith(f"{common_root}/"):
                    actual_filename = actual_filename[len(common_root) + 1:]
                    logger.debug(f"Stripped common root: {member.filename} -> {actual_filename}")

                # Skip if stripping left us with nothing
                if not actual_filename:
                    logger.debug(f"Skipping empty path after stripping root: {member.filename}")
                    continue

                # Skip system files, hidden files, and dangerous files
                if _should_skip_file(actual_filename):
                    logger.debug(f"Filtering out file: {actual_filename}")
                    continue

                # Sanitize the archive path
                try:
                    sanitized_path = _sanitize_archive_path(actual_filename)
                except BadRequestException as e:
                    logger.warning(f"Skipping invalid path {actual_filename}: {e}")
                    continue

                # Extract file content
                file_content = source_archive.read(member.filename)
                file_size = len(file_content)

                # Skip empty files
                if file_size == 0:
                    logger.debug(f"Skipping empty file: {member.filename}")
                    continue

                # Validate individual file (security check)
                file_stream = io.BytesIO(file_content)
                try:
                    # Basic validation for each file
                    guessed_type, _ = mimetypes.guess_type(sanitized_path)
                    content_type = guessed_type or "application/octet-stream"

                    # Perform security validation
                    perform_full_file_validation(
                        filename=sanitized_path.split("/")[-1],  # Get filename only
                        content_type=content_type,
                        file_size=file_size,
                        file_data=file_stream,
                    )
                except BadRequestException as e:
                    logger.warning(f"Skipping invalid file {member.filename}: {e}")
                    continue

                # Upload file to MinIO with structure: {group_id}/{version_identifier}/{sanitized_path}
                object_key = f"{submission_group.id}/{manual_version_identifier}/{sanitized_path}"

                storage_metadata = {
                    "submission_group_id": str(submission_group.id),
                    "version_identifier": manual_version_identifier,
                    "original_path": member.filename,
                }

                file_stream.seek(0)
                stored = await storage_service.upload_file(
                    file_data=file_stream,
                    object_key=object_key,
                    bucket_name=bucket_name,
                    content_type=content_type,
                    metadata=storage_metadata,
                )

                files_included.append({
                    "original_path": member.filename,
                    "sanitized_path": sanitized_path,
                    "object_key": object_key,
                    "size": file_size,
                })
                total_filtered_size += file_size

                logger.debug(f"Uploaded file to MinIO: {object_key} ({format_bytes(file_size)})")

            if not files_included:
                raise BadRequestException("No valid files found in archive after filtering")

    except zipfile.BadZipFile as exc:
        raise BadRequestException("Uploaded file is not a valid ZIP archive") from exc

    # Create single SubmissionArtifact record representing this submission
    # The object_key is the full path prefix in MinIO
    bucket_name = "submissions"
    object_key = f"{submission_group.id}/{manual_version_identifier}"  # Full path to version directory

    artifact_repo = SubmissionArtifactRepository(db, cache)
    artifact = SubmissionArtifact(
        submission_group_id=submission_group.id,
        uploaded_by_course_member_id=submitting_member.id,
        content_type="application/x-directory",  # Indicates this is a directory structure
        file_size=total_filtered_size,  # Total uncompressed size of all files
        bucket_name=bucket_name,
        object_key=object_key,  # Just the version_identifier
        version_identifier=manual_version_identifier,
        submit=submit,  # True = official submission, False = test/practice run
        properties={
            "files_count": len(files_included),
            "files_included": files_included,  # List of all files with their object_keys
            "original_filename": filename or "submission.zip",
            "total_size": total_filtered_size,
        }
    )

    # CRITICAL: Use repository for automatic cache invalidation
    created_artifact = artifact_repo.create(artifact)

    logger.info(
        "Created submission artifact %s for group %s with version %s (%d files, %s total, cache invalidated)",
        created_artifact.id,
        submission_group.id,
        manual_version_identifier,
        len(files_included),
        format_bytes(total_filtered_size),
    )

    return SubmissionUploadResponseModel(
        artifacts=[created_artifact.id],
        submission_group_id=submission_group.id,
        uploaded_by_course_member_id=submitting_member.id,
        total_size=total_filtered_size,
        files_count=len(files_included),
        uploaded_at=datetime.utcnow(),
        version_identifier=manual_version_identifier,
    )


async def download_submission_as_zip(
    artifact_id: UUID | str,
    permissions: Principal,
    db: Session,
    storage_service,
) -> tuple[io.BytesIO, str]:
    """
    Download a submission artifact and reconstruct it as a ZIP file.

    Returns:
        tuple[io.BytesIO, str]: (zip_buffer, filename)
    """
    # Check access permissions
    artifact = check_artifact_access(artifact_id, permissions, db)

    # Get list of files from properties
    files_included = artifact.properties.get("files_included", [])
    if not files_included:
        raise NotFoundException(detail="No files found in this submission")

    # Create ZIP file in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_info in files_included:
            object_key = file_info.get("object_key")
            sanitized_path = file_info.get("sanitized_path")

            if not object_key or not sanitized_path:
                logger.warning(f"Skipping file with missing info: {file_info}")
                continue

            try:
                # Download file from MinIO
                file_data = await storage_service.download_file(
                    object_key=object_key,
                    bucket_name=artifact.bucket_name
                )

                # Add to ZIP with sanitized path
                zip_file.writestr(sanitized_path, file_data)
                logger.debug(f"Added file to ZIP: {sanitized_path}")

            except Exception as e:
                logger.error(f"Failed to download file {object_key}: {e}")
                # Continue with other files
                continue

    # Reset buffer position
    zip_buffer.seek(0)

    # Generate filename
    filename = f"submission-{artifact.version_identifier}.zip"

    logger.info(
        "Created ZIP download for artifact %s with %d files",
        artifact_id,
        len(files_included)
    )

    return zip_buffer, filename


def check_artifact_access(
    artifact_id: UUID | str,
    permissions: Principal,
    db: Session,
    require_tutor: bool = False,
) -> SubmissionArtifact:
    """Check if user has access to a submission artifact."""
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
        is_group_member = db.query(SubmissionGroupMember).join(
            CourseMember
        ).filter(
            SubmissionGroupMember.submission_group_id == artifact.submission_group_id,
            CourseMember.user_id == user_id
        ).first()

        if not is_group_member:
            # Check for tutor/instructor permissions
            role_required = "_tutor" if require_tutor else "_student"
            has_elevated_perms = check_course_permissions(
                permissions, CourseMember, role_required, db
            ).filter(
                CourseMember.course_id == artifact.submission_group.course_id,
                CourseMember.user_id == user_id
            ).first()

            if not has_elevated_perms:
                raise ForbiddenException(detail="You don't have permission to access this artifact")

    return artifact


def get_artifact_with_details(
    artifact: SubmissionArtifact,
) -> SubmissionArtifactGet:
    """Build detailed artifact response with computed fields."""
    artifact_get = SubmissionArtifactGet.model_validate(artifact)

    # Add computed fields for the detailed view
    artifact_get.grades_count = len(artifact.grades) if hasattr(artifact, 'grades') else 0
    artifact_get.reviews_count = len(artifact.reviews) if hasattr(artifact, 'reviews') else 0
    artifact_get.test_results_count = len(artifact.test_results) if hasattr(artifact, 'test_results') else 0

    # Calculate average grade if there are grades
    if hasattr(artifact, 'grades') and artifact.grades:
        grades = [g.grade for g in artifact.grades if g.grade is not None]
        artifact_get.average_grade = sum(grades) / len(grades) if grades else None

    return artifact_get


def update_artifact(
    artifact_id: UUID | str,
    submit: Optional[bool],
    properties: Optional[dict],
    permissions: Principal,
    db: Session,
) -> SubmissionArtifact:
    """Update a submission artifact."""
    artifact = check_artifact_access(artifact_id, permissions, db, require_tutor=False)

    # Apply updates
    if submit is not None:
        artifact.submit = submit

    if properties is not None:
        artifact.properties = properties

    db.commit()
    db.refresh(artifact)

    logger.info("Updated submission artifact %s", artifact_id)

    return artifact


def create_artifact_grade(
    artifact_id: UUID | str,
    grade: float,
    status: str,
    comment: Optional[str],
    permissions: Principal,
    db: Session,
) -> SubmissionGrade:
    """Create a grade for an artifact. Requires instructor/tutor permissions."""

    # Get the artifact and verify permissions
    artifact = db.query(SubmissionArtifact).options(
        joinedload(SubmissionArtifact.submission_group).joinedload(SubmissionGroup.course)
    ).filter(SubmissionArtifact.id == artifact_id).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Check if user has grading permissions (must be at least tutor)
    course = artifact.submission_group.course

    # Query for course member with tutor or higher permission
    grader_member = check_course_permissions(
        permissions, CourseMember, "_tutor", db
    ).filter(
        CourseMember.course_id == course.id,
        CourseMember.user_id == permissions.get_user_id()
    ).first()

    if not grader_member:
        raise ForbiddenException(detail="You must be a tutor or instructor to grade artifacts")

    # Validate grade
    if grade < 0.0 or grade > 1.0:
        raise BadRequestException(detail="Grade must be between 0.0 and 1.0")

    # Create the grade (use the grader's course member id)
    grade_obj = SubmissionGrade(
        artifact_id=artifact_id,
        graded_by_course_member_id=grader_member.id,
        grade=grade,
        status=status,
        comment=comment,
    )

    db.add(grade_obj)
    db.commit()
    db.refresh(grade_obj)

    logger.info(f"Created grade {grade_obj.id} for artifact {artifact_id}")

    return grade_obj


def update_grade(
    grade_id: UUID | str,
    grade: Optional[float],
    status: Optional[str],
    comment: Optional[str],
    permissions: Principal,
    db: Session,
) -> SubmissionGrade:
    """Update an existing grade. Only the grader can update their own grade."""

    grade_obj = db.query(SubmissionGrade).options(
        joinedload(SubmissionGrade.graded_by)
    ).filter(SubmissionGrade.id == grade_id).first()

    if not grade_obj:
        raise NotFoundException(detail="Grade not found")

    # Check if user is the grader
    principal_user_id = permissions.get_user_id()
    if str(grade_obj.graded_by.user_id) != str(principal_user_id):
        raise ForbiddenException(detail="You can only update your own grades")

    # Update fields
    if grade is not None:
        grade_obj.grade = grade
    if status is not None:
        grade_obj.status = status
    if comment is not None:
        grade_obj.comment = comment

    # Validate grade
    if grade_obj.grade < 0.0 or grade_obj.grade > 1.0:
        raise BadRequestException(detail="Grade must be between 0.0 and 1.0")

    db.commit()
    db.refresh(grade_obj)

    return grade_obj


def delete_grade(
    grade_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> None:
    """Delete a grade. Only the grader or an admin can delete."""

    grade_obj = db.query(SubmissionGrade).filter(SubmissionGrade.id == grade_id).first()

    if not grade_obj:
        raise NotFoundException(detail="Grade not found")

    # Check permissions
    principal_user_id = permissions.get_user_id()
    if str(grade_obj.graded_by.user_id) != str(principal_user_id):
        # Check if user is instructor (higher permission needed to delete others' grades)
        course = grade_obj.artifact.submission_group.course
        is_instructor = check_course_permissions(
            permissions, CourseMember, "_lecturer", db  # Use _lecturer for instructor role
        ).filter(
            CourseMember.course_id == course.id,
            CourseMember.user_id == principal_user_id
        ).first()

        if not is_instructor:
            raise ForbiddenException(detail="Only instructors can delete other people's grades")

    db.delete(grade_obj)
    db.commit()

    logger.info(f"Deleted grade {grade_id}")


def create_artifact_review(
    artifact_id: UUID | str,
    body: str,
    review_type: str,
    permissions: Principal,
    db: Session,
) -> SubmissionReview:
    """Create a review for an artifact."""

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
        reviewer_course_member_id=course_member.id,
        body=body,
        review_type=review_type,
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    logger.info(f"Created review {review.id} for artifact {artifact_id}")

    return review


def update_review(
    review_id: UUID | str,
    body: Optional[str],
    review_type: Optional[str],
    permissions: Principal,
    db: Session,
) -> SubmissionReview:
    """Update an existing review. Only the reviewer can update their own review."""

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
    if body is not None:
        review.body = body
    if review_type is not None:
        review.review_type = review_type

    db.commit()
    db.refresh(review)

    return review


def delete_review(
    review_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> None:
    """Delete a review. Only the reviewer or an admin can delete."""

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


async def create_test_result(
    artifact_id: UUID | str,
    course_member_id: UUID | str,
    execution_backend_id: UUID | str,
    test_system_id: Optional[UUID | str],
    status: str,
    grade: Optional[float],
    result_json: Optional[dict],
    properties: Optional[dict],
    version_identifier: Optional[str],
    reference_version_identifier: Optional[str],
    permissions: Principal,
    db: Session,
) -> Result:
    """Create a test result for an artifact. Checks for test limitations."""

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
            Result.course_member_id == course_member_id,
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

    result = Result(
        submission_artifact_id=artifact_id,
        course_member_id=course_member.id,  # Use authenticated user's course member ID
        execution_backend_id=execution_backend_id,
        test_system_id=test_system_id,
        status=map_task_status_to_int(status),
        grade=grade,
        properties=properties,
        version_identifier=version_identifier,
        reference_version_identifier=reference_version_identifier,
    )

    db.add(result)
    db.commit()
    db.refresh(result)

    # Store result_json in MinIO if provided
    if result_json is not None:
        await store_result_json(result.id, result_json)

    logger.info(f"Created result {result.id} for artifact {artifact_id}")

    return result


async def update_test_result(
    test_id: UUID | str,
    status: Optional[str],
    grade: Optional[float],
    result_json: Optional[dict],
    properties: Optional[dict],
    finished_at: Optional[datetime],
    permissions: Principal,
    db: Session,
) -> Result:
    """Update a test result (e.g., when test completes). Only the test runner or admin can update."""

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

    # Update fields
    if status is not None:
        from computor_types.tasks import map_task_status_to_int
        result.status = map_task_status_to_int(status)
    if grade is not None:
        result.grade = grade
    if properties is not None:
        result.properties = properties
    if finished_at is not None:
        result.finished_at = finished_at

    db.commit()
    db.refresh(result)

    # Store/update result_json in MinIO if provided
    if result_json is not None:
        from computor_backend.services.result_storage import store_result_json
        await store_result_json(result.id, result_json)

    return result
