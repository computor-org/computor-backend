"""Computor API Client - Python HTTP client for Computor platform."""

__version__ = "0.1.0"

from .client import ComputorClient
from .base import BaseEndpointClient
from .advanced_base import (
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
    AccountsClient,
    CoursesClient,
    CourseFamiliesClient,
    CourseGroupsClient,
    CourseRolesClient,
    CourseContentKindClient,
    CourseContentTypesClient,
    CourseExecutionBackendsClient,
    ExampleRepositoriesClient,
    ExecutionBackendsClient,
    ExtensionsClient,
    GroupsClient,
    LanguagesClient,
    MessagesClient,
    OrganizationsClient,
    ProfilesClient,
    RolesClient,
    RoleClaimsClient,
    StudentProfilesClient,
    SubmissionGroupMembersClient,
    UserClient,
    UsersClient,
    UserRolesClient,
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
    "BaseEndpointClient",
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
    "AccountsClient",
    "CoursesClient",
    "CourseFamiliesClient",
    "CourseGroupsClient",
    "CourseRolesClient",
    "CourseContentKindClient",
    "CourseContentTypesClient",
    "CourseExecutionBackendsClient",
    "ExampleRepositoriesClient",
    "ExecutionBackendsClient",
    "ExtensionsClient",
    "GroupsClient",
    "LanguagesClient",
    "MessagesClient",
    "OrganizationsClient",
    "ProfilesClient",
    "RolesClient",
    "RoleClaimsClient",
    "StudentProfilesClient",
    "SubmissionGroupMembersClient",
    "UserClient",
    "UsersClient",
    "UserRolesClient",
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
