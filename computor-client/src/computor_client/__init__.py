"""Computor API Client - Python HTTP client for Computor platform."""

__version__ = "0.1.0"

from .client import ComputorClient
from .base import (
    # Base client classes
    SimpleEndpointClient,
    TypedEndpointClient,
    BaseEndpointClient,  # Alias for SimpleEndpointClient (backward compat)
    # Specialized client classes
    CustomActionClient,
    RoleBasedViewClient,
    FileOperationClient,
    TaskClient,
    AuthenticationClient,
)
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
    CourseContentTypeClient,
    ExampleRepositoryClient,
    ExtensionClient,
    GroupClient,
    LanguageClient,
    MessageClient,
    OrganizationClient,
    ProfileClient,
    RoleClient,
    RoleClaimClient,
    StudentProfileClient,
    SubmissionGroupMemberClient,
    UserClient,
    UserRoleClient,
)

# Import role-based clients
from .role_clients import (
    StudentViewClient,
    TutorViewClient,
    LecturerViewClient,
)

# Import custom clients
from .custom_clients import (
    ComputorAuthClient,
    StorageFileClient,
    ComputorTaskClient,
    SystemAdminClient,
    ExampleClient,
    SubmissionClient,
    TestExecutionClient,
    DeploymentClient,
)

__all__ = [
    # Main client
    "ComputorClient",
    # Base classes
    "SimpleEndpointClient",
    "TypedEndpointClient",
    "BaseEndpointClient",  # Alias for backward compatibility
    # Specialized classes
    "CustomActionClient",
    "RoleBasedViewClient",
    "FileOperationClient",
    "TaskClient",
    "AuthenticationClient",
    # Exceptions
    "ComputorClientError",
    "ComputorAPIError",
    "ComputorAuthenticationError",
    "ComputorAuthorizationError",
    "ComputorNotFoundError",
    "ComputorValidationError",
    "ComputorServerError",
    # Generated clients (CRUD)
    "AccountClient",
    "CourseClient",
    "CourseFamilyClient",
    "CourseGroupClient",
    "CourseRoleClient",
    "CourseContentKindClient",
    "CourseContentTypeClient",
    "ExampleRepositoryClient",
    "ExtensionClient",
    "GroupClient",
    "LanguageClient",
    "MessageClient",
    "OrganizationClient",
    "ProfileClient",
    "RoleClient",
    "RoleClaimClient",
    "StudentProfileClient",
    "SubmissionGroupMemberClient",
    "UserClient",
    "UserRoleClient",
    # Role-based view clients
    "StudentViewClient",
    "TutorViewClient",
    "LecturerViewClient",
    # Custom clients
    "ComputorAuthClient",
    "StorageFileClient",
    "ComputorTaskClient",
    "SystemAdminClient",
    "ExampleClient",
    "SubmissionClient",
    "TestExecutionClient",
    "DeploymentClient",
]
