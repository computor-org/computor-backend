"""
Repository layer for direct database access with optional caching.

This module provides repository classes for accessing database entities
with transparent write-through caching. All repositories support optional
caching via the cache parameter in their constructor.

Repositories included:
- BaseRepository: Abstract base class for entity repositories
- ViewRepository: Abstract base class for view repositories
- Entity repositories: Single-entity CRUD operations
- View repositories: Complex aggregated queries for student/tutor/lecturer views

Usage:
    # Entity repository (without cache)
    repo = OrganizationRepository(db)

    # Entity repository (with cache)
    from ctutor_backend.redis_cache import get_cache
    cache = get_cache()
    repo = OrganizationRepository(db, cache)

    # View repository (with cache)
    student_view = StudentViewRepository(db, cache)
    courses = student_view.list_courses(permissions, params)
"""

from .base import (
    BaseRepository,
    RepositoryError,
    NotFoundError,
    DuplicateError
)
from .view_base import ViewRepository
from .organization import OrganizationRepository
from .course import CourseRepository
from .course_family import CourseFamilyRepository
from .course_member import CourseMemberRepository
from .user import UserRepository
from .submission_group import SubmissionGroupRepository
from .submission_artifact import SubmissionArtifactRepository
from .result import ResultRepository
from .message import MessageRepository
from .example import ExampleRepository
from .course_content_repo import CourseContentRepository
from .example_version_repo import ExampleVersionRepository
from .submission_grade_repo import SubmissionGradeRepository
from .submission_group_member_repo import SubmissionGroupMemberRepository
from .course_content_deployment_repo import CourseContentDeploymentRepository
from .example_dependency_repo import ExampleDependencyRepository
from .student_view import StudentViewRepository
from .tutor_view import TutorViewRepository
from .lecturer_view import LecturerViewRepository

__all__ = [
    # Base classes
    "BaseRepository",
    "ViewRepository",
    "RepositoryError",
    "NotFoundError",
    "DuplicateError",
    # Entity repositories
    "OrganizationRepository",
    "CourseRepository",
    "CourseFamilyRepository",
    "CourseMemberRepository",
    "UserRepository",
    "SubmissionGroupRepository",
    "SubmissionArtifactRepository",
    "ResultRepository",
    "MessageRepository",
    "ExampleRepository",
    "CourseContentRepository",
    "ExampleVersionRepository",
    "SubmissionGradeRepository",
    "SubmissionGroupMemberRepository",
    "CourseContentDeploymentRepository",
    "ExampleDependencyRepository",
    # View repositories
    "StudentViewRepository",
    "TutorViewRepository",
    "LecturerViewRepository",
]
