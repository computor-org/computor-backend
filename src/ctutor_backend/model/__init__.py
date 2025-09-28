from .base import Base, metadata
from .auth import User, Account, Profile, StudentProfile, Session
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
    CourseSubmissionGroupGrading,
    CourseMemberComment
)
from .execution import ExecutionBackend
from .result import Result
from .role import Role, RoleClaim, UserRole
from .group import Group, GroupClaim, UserGroup
from .message import Message, MessageRead
from .example import Example, ExampleRepository, ExampleVersion, ExampleDependency
from .extension import Extension, ExtensionVersion
from .deployment import CourseContentDeployment, DeploymentHistory
from .artifact import SubmissionArtifact, ResultArtifact, TestResult, ArtifactGrade, ArtifactReview

# Import all models to ensure relationships are properly set up
from . import (
    auth,
    organization,
    role,
    group,
    execution,
    course,
    result,
    message,
    example,
    extension,
    deployment,
    artifact,
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
    'CourseSubmissionGroupGrading',
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
    'TestResult',
    'ArtifactGrade',
    'ArtifactReview',
]
