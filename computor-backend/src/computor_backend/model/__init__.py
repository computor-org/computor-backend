from .base import Base, metadata
from .auth import User, Account, Profile, StudentProfile, Session
from .language import Language
from .organization import Organization
from .course import (
    CourseContentKind,
    CourseRole,
    CourseFamily,
    Course,
    CourseContentType,
    CourseExecutionBackend,
    CourseGroup,
    CourseContent,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
    CourseMemberComment
)
from .execution import ExecutionBackend
from .result import Result
from .role import Role, RoleClaim, UserRole
from .group import Group, GroupClaim, UserGroup
from .message import Message, MessageRead
from .message_audit import MessageAuditLog, MessageAuditAction
from .example import Example, ExampleRepository, ExampleVersion, ExampleDependency
from .extension import Extension, ExtensionVersion
from .deployment import CourseContentDeployment, DeploymentHistory
from .artifact import SubmissionArtifact, ResultArtifact, SubmissionGrade, SubmissionReview
from .service import Service, ApiToken

# Import all models to ensure relationships are properly set up
from . import (
    auth,
    language,
    organization,
    role,
    group,
    execution,
    course,
    result,
    message,
    message_audit,
    example,
    extension,
    deployment,
    artifact,
    service,
)

__all__ = [
    'Base',
    'metadata',
    # Auth models
    'User',
    'Account',
    'Profile',
    'StudentProfile',
    'Session',
    # Language
    'Language',
    # Organization
    'Organization',
    # Course models
    'CourseContentKind',
    'CourseRole',
    'CourseFamily',
    'Course',
    'CourseContentType',
    'CourseExecutionBackend',
    'CourseGroup',
    'CourseContent',
    'CourseMember',
    'SubmissionGroup',
    'SubmissionGroupMember',
    'CourseMemberComment',
    # Execution
    'ExecutionBackend',
    # Result
    'Result',
    # Role/Permission models
    'Role',
    'RoleClaim',
    'UserRole',
    # Group models
    'Group',
    'GroupClaim',
    'UserGroup',
    # Message models
    'Message',
    'MessageRead',
    'MessageAuditLog',
    'MessageAuditAction',
    # Example models
    'ExampleRepository',
    'Example',
    'ExampleVersion',
    'ExampleDependency',
    # Extension registry models
    'Extension',
    'ExtensionVersion',
    # Deployment models
    'CourseContentDeployment',
    'DeploymentHistory',
    # Artifact models
    'SubmissionArtifact',
    'ResultArtifact',
    'SubmissionGrade',
    'SubmissionReview',
    # Service models
    'Service',
    'ApiToken',
]
