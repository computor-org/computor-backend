"""Read released student assignment descriptions without cloning a repository."""

import io
import re
import zipfile
from pathlib import PurePosixPath
from uuid import UUID

from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from computor_backend.business_logic.content_visibility import is_student_visible
from computor_backend.exceptions import BadRequestException, NotFoundException
from computor_backend.model.course import CourseContent
from computor_backend.model.deployment import DeploymentHistory
from computor_backend.permissions.course_access import get_course_member_or_403
from computor_backend.permissions.principal import Principal
from computor_backend.repositories.course_content_deployment_repo import (
    CourseContentDeploymentRepository,
)
from computor_backend.repositories.example_version_repo import ExampleVersionRepository
from computor_backend.services.storage_service import StorageService

# Keep the tutor ZIP layout, but expose only the public description surface.
# Other content/ files may contain authoring data rather than student assets.
_DESCRIPTION_NAME = re.compile(
    r"(?:index|readme)(?:_[a-z]{2,3}(?:[-_][a-z0-9]{2,8})?)?\.md", re.IGNORECASE
)
_ASSET_ROOTS = {"mediafiles", "assets", "images"}
_ASSET_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif", ".ico",
    ".pdf", ".mp3", ".mp4", ".wav", ".ogg", ".webm", ".csv", ".txt",
}
_PRIVATE_SEGMENTS = {
    "test", "tests", "hidden", "reference", "references", "solution", "solutions",
    "test.yaml", "test.yml", "meta.yaml", "meta.yml",
}
_PRIVATE_NAME = re.compile(r"(?:^|[-_.])(?:tests?|hidden|references?|solutions?)(?:$|[-_.])")


def student_description_filename(storage_path: str, object_name: str) -> str | None:
    """Return a safe ZIP member name, or None for private/unrelated objects."""
    prefix = storage_path.rstrip("/") + "/content/"
    if not object_name.startswith(prefix):
        return None
    relative = object_name[len(prefix):]
    # Check raw components before PurePosixPath can normalize '.' away.
    parts = relative.split("/")
    if (
        not relative or "\\" in relative
        or any(not part or part in {".", ".."} or part.startswith(".") for part in parts)
        or any(part.casefold() in _PRIVATE_SEGMENTS for part in parts)
    ):
        return None
    path = PurePosixPath(relative)
    if len(parts) == 1:
        return relative if _DESCRIPTION_NAME.fullmatch(relative) else None
    if parts[0].casefold() not in _ASSET_ROOTS or path.suffix.casefold() not in _ASSET_EXTENSIONS:
        return None
    if any(_PRIVATE_NAME.search(PurePosixPath(part).stem.casefold()) for part in parts[1:]):
        return None
    return relative


async def get_student_description(
    course_content_id: UUID, permissions: Principal, db: Session, storage_service: StorageService,
) -> StreamingResponse:
    """Download currently released, visible description files for a member.

    Authorization and release state bypass the student-view cache: revocation
    and hiding must take effect even if a recent course tree is cached. No
    submission group, local Git clone or staff reference route is used.
    """
    content = db.query(CourseContent).filter(
        CourseContent.id == str(course_content_id)
    ).first()
    if content is None or content.archived_at is not None:
        raise NotFoundException(detail="Course content is not available.")
    get_course_member_or_403(permissions, content.course_id, db)
    if not is_student_visible(db, content):
        raise NotFoundException(detail="Course content is not available.")

    deployment = CourseContentDeploymentRepository(db).find_latest_for_course_content(
        str(course_content_id)
    )
    # A pending version bump already points at its NEW example. Recover the
    # previous successful release from history instead of exposing staged work
    # or temporarily taking the student's existing instructions away.
    if (
        deployment is None or deployment.deployed_at is None
        or deployment.deployment_status == "unassigned"
    ):
        raise NotFoundException(detail="No released assignment description is available.")
    if deployment.deployment_status == "deployed":
        version_id = deployment.example_version_id
    else:
        released = db.query(DeploymentHistory).filter(
            DeploymentHistory.deployment_id == deployment.id,
            DeploymentHistory.action == "deployed",
        ).order_by(DeploymentHistory.created_at.desc()).first()
        version_id = released.example_version_id if released else None
    if not version_id:
        raise NotFoundException(detail="No released assignment description is available.")
    version = ExampleVersionRepository(db).get_with_relationships(version_id)
    if version is None or version.example is None or version.example.repository is None:
        raise NotFoundException(detail="Assignment description was not found.")
    repository = version.example.repository
    if repository.source_type not in {"minio", "s3"}:
        raise BadRequestException(detail="Description download is not supported for this repository.")
    if not version.storage_path or not repository.source_url:
        raise NotFoundException(detail="Assignment description was not found.")

    bucket = repository.source_url.split("/")[0]
    objects = await storage_service.list_objects(
        bucket_name=bucket, prefix=version.storage_path.rstrip("/") + "/content/"
    )
    buffer = io.BytesIO()
    filenames = set()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for obj in objects:
            filename = student_description_filename(version.storage_path, obj.object_name)
            if filename is None or filename in filenames:
                continue
            data = await storage_service.download_file(bucket_name=bucket, object_key=obj.object_name)
            archive.writestr(filename, data)
            filenames.add(filename)
    if not any(_DESCRIPTION_NAME.fullmatch(name) for name in filenames):
        raise NotFoundException(detail="No assignment description files were found.")
    buffer.seek(0)
    # Fixed name avoids putting untrusted course titles into HTTP headers.
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="assignment_description.zip"',
            "Cache-Control": "private, no-store",
        },
    )
