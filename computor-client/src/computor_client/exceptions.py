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
        default = f"User not found: {user_id}" if user_id else "User not found"
        super().__init__(
            message or default,
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
        default = f"Course not found: {course_id}" if course_id else "Course not found"
        super().__init__(
            message or default,
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

# Map HTTP status codes to exception classes. This is the single source of
# truth: ``raise_for_response`` and ``exception_from_response`` both consult it,
# so they can no longer disagree (503 used to map to ServiceUnavailableError in
# one and ServerError in the other).
STATUS_CODE_EXCEPTIONS = {
    400: ValidationError,
    401: AuthenticationError,
    403: AuthorizationError,
    404: NotFoundError,
    409: ConflictError,
    422: ValidationError,
    429: RateLimitError,
    500: ServerError,
    502: ServerError,
    503: ServiceUnavailableError,
    504: ServerError,
}

# Codes that identify a more specific failure than the status alone. Only
# subclasses that take the standard ``(message, *, error_code, details)``
# signature belong here.
ERROR_CODE_EXCEPTIONS = {
    "AUTH_002": InvalidCredentialsError,
    "AUTH_003": TokenExpiredError,
    "AUTHZ_002": AdminRequiredError,
    "AUTHZ_003": CourseAccessDeniedError,
}


def _exception_class_for(status_code: int, error_code: Optional[str]):
    """Pick the most specific exception class for a status/error-code pair."""
    if error_code and error_code in ERROR_CODE_EXCEPTIONS:
        return ERROR_CODE_EXCEPTIONS[error_code]
    if status_code in STATUS_CODE_EXCEPTIONS:
        return STATUS_CODE_EXCEPTIONS[status_code]
    if 500 <= status_code < 600:
        return ServerError
    return ComputorClientError


def _coerce_message(value: Any) -> str:
    """Render an error body's message field as a string.

    FastAPI's own 422 handler (and some proxies) put a *list* of per-field
    dicts in ``detail``. Passing that through unchanged made ``str(exc)`` blow
    up with a TypeError inside the caller's ``except`` block — which is exactly
    where an error message is least welcome.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                loc = item.get("loc") or item.get("field")
                msg = item.get("msg") or item.get("message") or str(item)
                if isinstance(loc, (list, tuple)):
                    loc = ".".join(str(p) for p in loc)
                parts.append(f"{loc}: {msg}" if loc else str(msg))
            else:
                parts.append(str(item))
        return "; ".join(parts)
    return str(value)


def _field_errors_from(details: Dict[str, Any]) -> Dict[str, str]:
    """Flatten the backend's ``details.validation_errors`` into field -> message."""
    errors = details.get("validation_errors")
    if not isinstance(errors, list):
        return {}
    out: Dict[str, str] = {}
    for item in errors:
        if isinstance(item, dict) and item.get("field"):
            out[str(item["field"])] = str(item.get("message", ""))
    return out


def raise_for_response(response) -> None:
    """Raise the appropriate ``ComputorClientError`` for an error HTTP response.

    Shared by the async HTTP client and the sync facade so both map responses to
    typed exceptions identically. No-op for 2xx responses.

    The backend answers errors with ``{"message", "error_code", "details"}``;
    ``details.validation_errors`` carries the per-field reasons, which are
    surfaced as ``ValidationError.field_errors`` rather than being dropped.
    """
    status_code = response.status_code
    if status_code < 400:
        return

    details: Dict[str, Any] = {}
    error_code = None
    try:
        error_data = response.json()
    except Exception:
        error_data = None

    if isinstance(error_data, dict):
        raw_detail = error_data.get("detail")
        if raw_detail is None:
            raw_detail = error_data.get("message")
        detail = _coerce_message(raw_detail) if raw_detail is not None else str(error_data)
        error_code = error_data.get("error_code")
        if isinstance(error_data.get("details"), dict):
            details = error_data["details"]
    else:
        detail = response.text or f"HTTP {status_code}"

    exception_class = _exception_class_for(status_code, error_code)
    kwargs: Dict[str, Any] = {"error_code": error_code, "details": details or None}

    # The promoted subclasses pin their own status code.
    if exception_class not in ERROR_CODE_EXCEPTIONS.values():
        kwargs["status_code"] = status_code

    if exception_class is ValidationError:
        kwargs["field_errors"] = _field_errors_from(details) or None
    elif exception_class is RateLimitError:
        retry_after = response.headers.get("Retry-After")
        kwargs["retry_after"] = int(retry_after) if retry_after and retry_after.isdigit() else None

    raise exception_class(detail, **kwargs)


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
    exception_class = _exception_class_for(status_code, error_code)
    if exception_class in ERROR_CODE_EXCEPTIONS.values():
        # These pin their own status code.
        return exception_class(message, error_code=error_code, details=details)
    return exception_class(
        message,
        status_code=status_code,
        error_code=error_code,
        details=details,
    )
