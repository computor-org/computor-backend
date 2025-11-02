"""
Backend-specific interfaces that extend computor-types with SQLAlchemy models.

This module provides fully-equipped interface classes for use within the backend.
Each interface class:
- Extends the corresponding interface from computor-types
- Sets the SQLAlchemy model attribute
- Provides search functions for repository use

These interfaces bridge the gap between pure DTOs (computor-types) and
backend database operations.
"""

from computor_backend.interfaces.user import UserInterface
from computor_backend.interfaces.organization import OrganizationInterface
from computor_backend.interfaces.course import CourseInterface
from computor_backend.interfaces.course_family import CourseFamilyInterface
from computor_backend.interfaces.course_content import CourseContentInterface
from computor_backend.interfaces.course_member import CourseMemberInterface
from computor_backend.interfaces.account import AccountInterface
from computor_backend.interfaces.profile import ProfileInterface
from computor_backend.interfaces.student_profile import StudentProfileInterface
from computor_backend.interfaces.role import RoleInterface
from computor_backend.interfaces.role_claim import RoleClaimInterface
from computor_backend.interfaces.user_role import UserRoleInterface
from computor_backend.interfaces.example import ExampleInterface, ExampleRepositoryInterface
from computor_backend.interfaces.extension import ExtensionInterface
from computor_backend.interfaces.message import MessageInterface
from computor_backend.interfaces.result import ResultInterface

# Minimal backend wrappers for lookup-type interfaces
# Legacy execution_backend interfaces removed - replaced by ServiceType
from computor_backend.interfaces.service_type import ServiceTypeInterface
from computor_backend.interfaces.service import ServiceInterface
from computor_backend.interfaces.api_token import ApiTokenInterface
from computor_backend.interfaces.groups import GroupInterface
from computor_backend.interfaces.sessions import SessionInterface
from computor_backend.interfaces.submission_group_members import SubmissionGroupMemberInterface
from computor_backend.interfaces.submission_groups import SubmissionGroupInterface
from computor_backend.interfaces.course_groups import CourseGroupInterface
from computor_backend.interfaces.course_roles import CourseRoleInterface
from computor_backend.interfaces.course_content_types import CourseContentTypeInterface
from computor_backend.interfaces.course_content_kind import CourseContentKindInterface
from computor_backend.interfaces.languages import LanguageInterface

__all__ = [
    "UserInterface",
    "OrganizationInterface",
    "CourseInterface",
    "CourseFamilyInterface",
    "CourseContentInterface",
    "CourseMemberInterface",
    "AccountInterface",
    "ProfileInterface",
    "StudentProfileInterface",
    "RoleInterface",
    "RoleClaimInterface",
    "UserRoleInterface",
    "ExampleInterface",
    "ExampleRepositoryInterface",
    "ExtensionInterface",
    "MessageInterface",
    "ResultInterface",
    "ServiceTypeInterface",
    "ServiceInterface",
    "ApiTokenInterface",
    "GroupInterface",
    "SessionInterface",
    "SubmissionGroupMemberInterface",
    "SubmissionGroupInterface",
    "CourseGroupInterface",
    "CourseRoleInterface",
    "CourseContentTypeInterface",
    "CourseContentKindInterface",
    "LanguageInterface",
]
