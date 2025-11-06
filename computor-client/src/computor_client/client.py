"""Main Computor API client class."""

from typing import Optional
import httpx

from .generated import (
    AccountClient,
    ApiTokenClient,
    CourseContentClient,
    CourseContentKindClient,
    CourseContentTypeClient,
    CourseFamilyClient,
    CourseGroupClient,
    CourseMemberClient,
    CourseRoleClient,
    CourseClient,
    ExampleClient as GeneratedExampleClient,
    ExampleRepositoryClient,
    ExtensionClient,
    GroupClient,
    LanguageClient,
    MessageClient,
    OrganizationClient,
    ProfileClient,
    ResultClient,
    RoleClaimClient,
    RoleClient,
    ServiceClient,
    ServiceTypeClient,
    SessionClient,
    StudentProfileClient,
    SubmissionGroupClient,
    SubmissionGroupMemberClient,
    UserClient,
    UserRoleClient,
)

# Import custom clients
from .role_clients import (
    StudentViewClient,
    TutorViewClient,
    LecturerViewClient,
)

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


class ComputorClient:
    """
    Main client for Computor API.

    Provides access to all API endpoints through specialized client instances.

    Usage:
        async with ComputorClient(base_url="http://localhost:8000") as client:
            # Authenticate
            await client.authenticate(username="admin", password="secret")

            # Use endpoint clients
            orgs = await client.organizations.list()
            user = await client.users.get("user-id")
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        headers: Optional[dict] = None,
    ):
        """
        Initialize Computor API client.

        Args:
            base_url: Base URL of the API (e.g., "http://localhost:8000")
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            headers: Additional headers to include in all requests
        """
        self.base_url = base_url.rstrip('/')

        # Initialize httpx client
        default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            default_headers.update(headers)

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            verify=verify_ssl,
            headers=default_headers,
        )

        # Initialize generated endpoint clients
        self.accounts = AccountClient(self._client)
        self.api_tokens = ApiTokenClient(self._client)
        self.courses = CourseClient(self._client)
        self.course_contents = CourseContentClient(self._client)
        self.course_content_kinds = CourseContentKindClient(self._client)
        self.course_content_types = CourseContentTypeClient(self._client)
        self.course_families = CourseFamilyClient(self._client)
        self.course_groups = CourseGroupClient(self._client)
        self.course_members = CourseMemberClient(self._client)
        self.course_roles = CourseRoleClient(self._client)
        self.example_repositories = ExampleRepositoryClient(self._client)
        self.extensions = ExtensionClient(self._client)
        self.groups = GroupClient(self._client)
        self.languages = LanguageClient(self._client)
        self.messages = MessageClient(self._client)
        self.organizations = OrganizationClient(self._client)
        self.profiles = ProfileClient(self._client)
        self.results = ResultClient(self._client)
        self.roles = RoleClient(self._client)
        self.role_claims = RoleClaimClient(self._client)
        self.services = ServiceClient(self._client)
        self.service_types = ServiceTypeClient(self._client)
        self.sessions = SessionClient(self._client)
        self.student_profiles = StudentProfileClient(self._client)
        self.submission_groups = SubmissionGroupClient(self._client)
        self.submission_group_members = SubmissionGroupMemberClient(self._client)
        self.user = UserClient(self._client)
        self.user_roles = UserRoleClient(self._client)

        # Custom clients with enhanced functionality (override generated clients)
        self.auth = ComputorAuthClient(self._client)
        self.storage = StorageFileClient(self._client)
        self.tasks = ComputorTaskClient(self._client)
        self.system = SystemAdminClient(self._client)
        self.examples = ExampleClient(self._client)
        self.submissions = SubmissionClient(self._client)
        self.tests = TestExecutionClient(self._client)
        self.deploy = DeploymentClient(self._client)

        # Role-based view clients
        self.student_view = StudentViewClient(self._client)
        self.tutor_view = TutorViewClient(self._client)
        self.lecturer_view = LecturerViewClient(self._client)

    async def authenticate(self, username: str, password: str) -> dict:
        """
        Authenticate with the API and store the token.

        Args:
            username: Username for authentication
            password: Password for authentication

        Returns:
            Authentication response with token
        """
        response = await self._client.post(
            "/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()

        data = response.json()
        token = data.get("access_token")

        if token:
            # Update authorization header for all future requests
            self._client.headers["Authorization"] = f"Bearer {token}"

        return data

    async def set_token(self, token: str):
        """
        Set authentication token directly.

        Args:
            token: API token for authentication (uses X-API-Token header for API tokens starting with 'ctp_', Bearer for JWT)
        """
        # API tokens start with 'ctp_' and use X-API-Token header
        if token.startswith("ctp_"):
            self._client.headers["X-API-Token"] = token
            # Remove Authorization header if present
            self._client.headers.pop("Authorization", None)
        else:
            # JWT tokens use Authorization Bearer
            self._client.headers["Authorization"] = f"Bearer {token}"
            # Remove X-API-Token header if present
            self._client.headers.pop("X-API-Token", None)

    async def close(self):
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
