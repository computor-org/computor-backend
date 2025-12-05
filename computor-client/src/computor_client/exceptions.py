"""
Exception hierarchy for the Computor client library.

This module provides a comprehensive set of exceptions that map to HTTP status codes
and error responses from the Computor API. Each exception preserves the error code
and additional context from the server response.
"""

from typing import Any, Dict, Optional


class ComputorClientError(Exception):
    """
    Base exception for all Computor client errors.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (if applicable)
        error_code: Computor error code (e.g., "AUTH_001")
        details: Additional error details from the response
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        parts = [self.message]
        if self.error_code:
            parts.insert(0, f"[{self.error_code}]")
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        return " ".join(parts)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"status_code={self.status_code}, "
            f"error_code={self.error_code!r})"
        )


# =============================================================================
# Authentication Errors (401)
# =============================================================================


class AuthenticationError(ComputorClientError):
    """
    Authentication failed or credentials are invalid.

    Raised when:
    - No authentication credentials provided
    - Invalid username/password
    - Expired or invalid access token
    - Token refresh failed
    """

    def __init__(
        self,
        message: str = "Authentication required",
        *,
        status_code: int = 401,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            details=details,
        )


class TokenExpiredError(AuthenticationError):
    """
    Access token has expired.

    The client should attempt to refresh the token using the refresh token.
    """

    def __init__(
        self,
        message: str = "Access token has expired",
        *,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            status_code=401,
            error_code=error_code or "AUTH_003",
            details=details,
        )


class InvalidCredentialsError(AuthenticationError):
    """Invalid username or password."""

    def __init__(
        self,
        message: str = "Invalid username or password",
        *,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            status_code=401,
            error_code=error_code or "AUTH_002",
            details=details,
        )


# =============================================================================
# Authorization Errors (403)
# =============================================================================


class AuthorizationError(ComputorClientError):
    """
    Access denied due to insufficient permissions.

    Raised when the authenticated user doesn't have permission to perform
    the requested operation.
    """

    def __init__(
        self,
        message: str = "Access denied",
        *,
        status_code: int = 403,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            details=details,
        )


class AdminRequiredError(AuthorizationError):
    """Admin privileges are required for this operation."""

    def __init__(
        self,
        message: str = "Admin privileges required",
        *,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            status_code=403,
            error_code=error_code or "AUTHZ_002",
            details=details,
        )


class CourseAccessDeniedError(AuthorizationError):
    """Access to the specified course is denied."""

    def __init__(
        self,
        message: str = "Course access denied",
        *,
        course_id: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if course_id:
            details = details or {}
            details["course_id"] = course_id
        super().__init__(
            message,
            status_code=403,
            error_code=error_code or "AUTHZ_003",
            details=details,
        )


# =============================================================================
# Validation Errors (400)
# =============================================================================


class ValidationError(ComputorClientError):
    """
    Request validation failed.

    Raised when the request data doesn't meet validation requirements.
    """

    def __init__(
        self,
        message: str = "Validation error",
        *,
        status_code: int = 400,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        field_errors: Optional[Dict[str, str]] = None,
    ):
        if field_errors:
            details = details or {}
            details["field_errors"] = field_errors
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            details=details,
        )
        self.field_errors = field_errors or {}


class MissingFieldError(ValidationError):
    """A required field is missing from the request."""

    def __init__(
        self,
        field_name: str,
        *,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message or f"Required field missing: {field_name}",
            status_code=400,
            error_code=error_code or "VAL_002",
            details=details,
            field_errors={field_name: "This field is required"},
        )
        self.field_name = field_name


class InvalidFieldFormatError(ValidationError):
    """A field has an invalid format."""

    def __init__(
        self,
        field_name: str,
        expected_format: str,
        *,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message or f"Invalid format for field '{field_name}': expected {expected_format}",
            status_code=400,
            error_code=error_code or "VAL_003",
            details=details,
            field_errors={field_name: f"Expected format: {expected_format}"},
        )
        self.field_name = field_name
        self.expected_format = expected_format


# =============================================================================
# Not Found Errors (404)
# =============================================================================


class NotFoundError(ComputorClientError):
    """
    Requested resource was not found.

    Raised when the API returns a 404 status code.
    """

    def __init__(
        self,
        message: str = "Resource not found",
        *,
        status_code: int = 404,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        if resource_type or resource_id:
            details = details or {}
            if resource_type:
                details["resource_type"] = resource_type
            if resource_id:
                details["resource_id"] = resource_id
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            details=details,
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class UserNotFoundError(NotFoundError):
    """The specified user was not found."""

    def __init__(
        self,
        user_id: Optional[str] = None,
        *,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message or f"User not found: {user_id}" if user_id else "User not found",
            status_code=404,
            error_code=error_code or "NF_002",
            details=details,
            resource_type="user",
            resource_id=user_id,
        )


class CourseNotFoundError(NotFoundError):
    """The specified course was not found."""

    def __init__(
        self,
        course_id: Optional[str] = None,
        *,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message or f"Course not found: {course_id}" if course_id else "Course not found",
            status_code=404,
            error_code=error_code or "NF_003",
            details=details,
            resource_type="course",
            resource_id=course_id,
        )


# =============================================================================
# Conflict Errors (409)
# =============================================================================


class ConflictError(ComputorClientError):
    """
    Request conflicts with current state of the resource.

    Raised when attempting to create a resource that already exists
    or update a resource that has been modified.
    """

    def __init__(
        self,
        message: str = "Resource conflict",
        *,
        status_code: int = 409,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            details=details,
        )


class ResourceExistsError(ConflictError):
    """A resource with the same identifier already exists."""

    def __init__(
        self,
        resource_type: str,
        identifier: str,
        *,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message or f"{resource_type} already exists: {identifier}",
            status_code=409,
            error_code=error_code or "CONFLICT_001",
            details=details,
        )
        self.resource_type = resource_type
        self.identifier = identifier


# =============================================================================
# Rate Limit Errors (429)
# =============================================================================


class RateLimitError(ComputorClientError):
    """
    Rate limit exceeded.

    The client should wait before retrying. The retry_after attribute
    indicates how many seconds to wait.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        status_code: int = 429,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ):
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            details=details,
        )
        self.retry_after = retry_after


# =============================================================================
# Server Errors (5xx)
# =============================================================================


class ServerError(ComputorClientError):
    """
    Server-side error occurred.

    Raised when the API returns a 5xx status code.
    """

    def __init__(
        self,
        message: str = "Server error",
        *,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            details=details,
        )


class ServiceUnavailableError(ServerError):
    """The service is temporarily unavailable."""

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        *,
        status_code: int = 503,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ):
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            details=details,
        )
        self.retry_after = retry_after


# =============================================================================
# Network Errors (Client-side)
# =============================================================================


class NetworkError(ComputorClientError):
    """
    Network-level error occurred.

    Raised when there's a connection problem, DNS failure, or other
    network-related issues.
    """

    def __init__(
        self,
        message: str = "Network error",
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            status_code=None,
            error_code=None,
            details=details,
        )


class TimeoutError(NetworkError):
    """Request timed out."""

    def __init__(
        self,
        message: str = "Request timed out",
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details=details)


class ConnectionError(NetworkError):
    """Failed to establish connection to the server."""

    def __init__(
        self,
        message: str = "Failed to connect to server",
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details=details)


# =============================================================================
# Exception Mapping
# =============================================================================

# Map HTTP status codes to exception classes
STATUS_CODE_EXCEPTIONS = {
    400: ValidationError,
    401: AuthenticationError,
    403: AuthorizationError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
    500: ServerError,
    502: ServerError,
    503: ServiceUnavailableError,
    504: ServerError,
}


def exception_from_response(
    status_code: int,
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> ComputorClientError:
    """
    Create an appropriate exception from an HTTP response.

    Args:
        status_code: HTTP status code
        message: Error message
        error_code: Computor error code
        details: Additional error details

    Returns:
        Appropriate ComputorClientError subclass
    """
    exception_class = STATUS_CODE_EXCEPTIONS.get(status_code, ComputorClientError)
    return exception_class(
        message,
        status_code=status_code,
        error_code=error_code,
        details=details,
    )
