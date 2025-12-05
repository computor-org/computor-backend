"""
Computor Client Library.

A type-safe async HTTP client for the Computor API.

Example usage:
    ```python
    from computor_client import ComputorClient

    async with ComputorClient(base_url="http://localhost:8000") as client:
        # Authenticate
        await client.login(username="admin", password="secret")

        # List resources
        orgs = await client.organizations.list()

        # Get a single resource
        user = await client.users.get("user-id")

        # Create a resource
        from computor_types.courses import CourseCreate
        course = await client.courses.create(CourseCreate(
            name="My Course",
            ...
        ))
    ```

For more examples, see the documentation.
"""

__version__ = "0.2.0"

# Main client
from computor_client.client import ComputorClient

# HTTP client components (for advanced usage)
from computor_client.http import (
    AsyncHTTPClient,
    AuthProvider,
    TokenAuthProvider,
)

# Base classes (for building custom clients)
from computor_client.base import (
    BaseEndpointClient,
    ReadOnlyEndpointClient,
    CRUDEndpointClient,
    TypedEndpointClient,
)

# Exceptions
from computor_client.exceptions import (
    # Base exception
    ComputorClientError,
    # Authentication errors
    AuthenticationError,
    TokenExpiredError,
    InvalidCredentialsError,
    # Authorization errors
    AuthorizationError,
    AdminRequiredError,
    CourseAccessDeniedError,
    # Validation errors
    ValidationError,
    MissingFieldError,
    InvalidFieldFormatError,
    # Not found errors
    NotFoundError,
    UserNotFoundError,
    CourseNotFoundError,
    # Conflict errors
    ConflictError,
    ResourceExistsError,
    # Rate limiting
    RateLimitError,
    # Server errors
    ServerError,
    ServiceUnavailableError,
    # Network errors
    NetworkError,
    TimeoutError,
    ConnectionError,
    # Utility
    exception_from_response,
)

__all__ = [
    # Version
    "__version__",
    # Main client
    "ComputorClient",
    # HTTP components
    "AsyncHTTPClient",
    "AuthProvider",
    "TokenAuthProvider",
    # Base classes
    "BaseEndpointClient",
    "ReadOnlyEndpointClient",
    "CRUDEndpointClient",
    "TypedEndpointClient",
    # Exceptions
    "ComputorClientError",
    "AuthenticationError",
    "TokenExpiredError",
    "InvalidCredentialsError",
    "AuthorizationError",
    "AdminRequiredError",
    "CourseAccessDeniedError",
    "ValidationError",
    "MissingFieldError",
    "InvalidFieldFormatError",
    "NotFoundError",
    "UserNotFoundError",
    "CourseNotFoundError",
    "ConflictError",
    "ResourceExistsError",
    "RateLimitError",
    "ServerError",
    "ServiceUnavailableError",
    "NetworkError",
    "TimeoutError",
    "ConnectionError",
    "exception_from_response",
]
