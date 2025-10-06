"""Computor API Client - Python HTTP client for Computor platform."""

__version__ = "0.1.0"

from .client import ComputorClient
from .base import BaseEndpointClient
from .exceptions import (
    ComputorClientError,
    ComputorAPIError,
    ComputorAuthenticationError,
    ComputorAuthorizationError,
    ComputorNotFoundError,
    ComputorValidationError,
    ComputorServerError,
)

# Re-export all generated clients
from .generated import (
    AccountClient,
    CourseClient,
    CourseFamilyClient,
    CourseGroupClient,
    CourseRoleClient,
    CourseContentKindClient,
    CourseContentDeploymentClient,
    CourseExecutionBackendClient,
    CourseTutorClient,
    DeploymentHistoryClient,
    ExampleClient,
    ExampleRepositoryClient,
    ExecutionBackendClient,
    ExtensionClient,
    GroupClient,
    GroupClaimClient,
    LanguageClient,
    MessageClient,
    OrganizationClient,
    ProfileClient,
    RoleClient,
    RoleClaimClient,
    StorageClient,
    StudentProfileClient,
    SubmissionGroupMemberClient,
    UserClient,
    UserGroupClient,
)

__all__ = [
    # Main client
    "ComputorClient",
    # Base classes
    "BaseEndpointClient",
    # Exceptions
    "ComputorClientError",
    "ComputorAPIError",
    "ComputorAuthenticationError",
    "ComputorAuthorizationError",
    "ComputorNotFoundError",
    "ComputorValidationError",
    "ComputorServerError",
    # Generated clients
    "AccountClient",
    "CourseClient",
    "CourseFamilyClient",
    "CourseGroupClient",
    "CourseRoleClient",
    "CourseContentKindClient",
    "CourseContentDeploymentClient",
    "CourseExecutionBackendClient",
    "CourseTutorClient",
    "DeploymentHistoryClient",
    "ExampleClient",
    "ExampleRepositoryClient",
    "ExecutionBackendClient",
    "ExtensionClient",
    "GroupClient",
    "GroupClaimClient",
    "LanguageClient",
    "MessageClient",
    "OrganizationClient",
    "ProfileClient",
    "RoleClient",
    "RoleClaimClient",
    "StorageClient",
    "StudentProfileClient",
    "SubmissionGroupMemberClient",
    "UserClient",
    "UserGroupClient",
]
