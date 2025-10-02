"""Business logic for filesystem operations."""
import os
from uuid import UUID
from sqlalchemy.orm import Session
from aiocache import SimpleMemoryCache

from ctutor_backend.interface.course_contents import CourseContentInterface
from ctutor_backend.interface.courses import CourseInterface
from ctutor_backend.interface.base import EntityInterface
from ctutor_backend.model.course import Course, CourseContent, CourseFamily
from ctutor_backend.model.organization import Organization
from ctutor_backend.generator.git_helper import clone_or_pull_and_checkout
from ctutor_backend.settings import settings

_local_git_cache = SimpleMemoryCache()
_expiry_time = 900  # in seconds


async def cached_clone_or_pull_and_checkout(
    source_directory_checkout: str,
    full_https_git_path: str,
    token: str,
    commit: str
) -> str:
    """Clone or pull a git repository with caching.

    Args:
        source_directory_checkout: Local directory to checkout to
        full_https_git_path: Full HTTPS git repository path
        token: Authentication token
        commit: Commit hash to checkout

    Returns:
        Commit hash
    """
    obj = await _local_git_cache.get(f"{source_directory_checkout}::{full_https_git_path}")

    if obj is not None and obj == commit and os.path.exists(os.path.join(source_directory_checkout, ".git")):
        return obj
    else:
        clone_or_pull_and_checkout(source_directory_checkout, full_https_git_path, token, commit)
        await _local_git_cache.set(f"{source_directory_checkout}::{full_https_git_path}", commit, _expiry_time)
        return commit


async def mirror_entity_to_filesystem(
    id: UUID | str,
    interface: EntityInterface,
    db: Session
) -> None:
    """Mirror an entity to filesystem (not implemented yet).

    Args:
        id: Entity ID
        interface: Entity interface
        db: Database session
    """
    # Not implemented yet
    pass


async def mirror_db_to_filesystem(db: Session) -> None:
    """Mirror all courses and course contents to filesystem.

    Args:
        db: Database session
    """
    courses = db.scalars(db.query(Course.id)).all()
    course_contents = db.scalars(db.query(CourseContent.id)).all()

    for item in courses:
        try:
            await mirror_entity_to_filesystem(item, CourseInterface, db)
        except Exception as e:
            print(f"Mirroring course with id {item} failed. Reason: {e.args}")

    for item in course_contents:
        try:
            await mirror_entity_to_filesystem(item, CourseContentInterface, db)
        except Exception as e:
            print(f"Mirroring course_content with id {item} failed. Reason: {e.args}")


async def get_path_course(id: str | UUID, db: Session) -> str:
    """Get the filesystem path for a course.

    Args:
        id: Course ID
        db: Database session

    Returns:
        Full filesystem path to course directory
    """
    path = await _local_git_cache.get(f"dir:courses:{id}")

    if path is not None:
        return path

    query = db.query(Organization.path, CourseFamily.path, Course.path) \
        .join(CourseFamily, CourseFamily.id == Course.course_family_id) \
        .join(Organization, Organization.id == CourseFamily.organization_id) \
        .filter(Course.id == id).first()

    path = os.path.join(settings.API_LOCAL_STORAGE_DIR, "courses")

    for segment in query:
        path = os.path.join(path, str(segment))

    await _local_git_cache.set(f"dir:courses:{id}", path, 36000)

    return path


async def get_path_course_content(id: str | UUID, db: Session) -> str:
    """Get the filesystem path for a course content.

    Args:
        id: Course content ID
        db: Database session

    Returns:
        Full filesystem path to course content directory
    """
    path = await _local_git_cache.get(f"dir:course-contents:{id}")

    if path is not None:
        return path

    query = db.query(Organization.path, CourseFamily.path, Course.path, CourseContent.path) \
        .join(Course, Course.id == CourseContent.course_id) \
        .join(CourseFamily, CourseFamily.id == Course.course_family_id) \
        .join(Organization, Organization.id == CourseFamily.organization_id) \
        .filter(CourseContent.id == id).first()

    path = os.path.join(settings.API_LOCAL_STORAGE_DIR, "course-contents")

    for segment in query:
        path = os.path.join(path, str(segment))

    await _local_git_cache.set(f"dir:course-contents:{id}", path, 36000)

    return path
