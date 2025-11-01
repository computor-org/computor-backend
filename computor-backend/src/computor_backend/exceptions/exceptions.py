"""
Enhanced exception handling with error codes and rich metadata.

This module provides custom HTTP exceptions that integrate with the error registry
to provide consistent, informative error responses with unique error codes.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status
import traceback
import inspect
from datetime import datetime, timezone

from computor_types.errors import ErrorMetadata, ErrorResponse, ErrorDebugInfo


class ComputorException(HTTPException):
    """
    Base exception class for all Computor exceptions.

    Provides rich error handling with:
    - Unique error codes from registry
    - Structured error responses
    - Debug information in development mode
    - Context metadata for logging and debugging
    """

    def __init__(
        self,
        error_code: str,
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """
        Initialize exception with error code and metadata.

        Args:
            error_code: Error code from error registry (e.g., "AUTH_001")
            detail: Additional detail message (overrides registry message if provided)
            headers: HTTP response headers
            context: Additional context for debugging
            user_id: User ID if available
            request_id: Request ID for tracing
        """
        self.error_code = error_code
        self.context = context or {}
        self.user_id = user_id
        self.request_id = request_id

        # Get caller information for debugging
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller_frame = frame.f_back.f_back  # Skip this __init__ and the subclass __init__
            if caller_frame:
                self.function_name = caller_frame.f_code.co_name
                self.file_name = caller_frame.f_code.co_filename
                self.line_number = caller_frame.f_lineno
            else:
                self.function_name = None
                self.file_name = None
                self.line_number = None
        else:
            self.function_name = None
            self.file_name = None
            self.line_number = None

        # Initialize parent HTTPException
        # The actual status_code and detail will be set by subclasses
        super().__init__(status_code=500, detail=detail, headers=headers)

    def to_error_response(self, include_debug: bool = False) -> ErrorResponse:
        """
        Convert exception to structured ErrorResponse.

        Args:
            include_debug: Whether to include debug information (dev mode only)

        Returns:
            ErrorResponse with error code, message, and optional debug info
        """
        from computor_backend.exceptions.error_registry import get_error_definition

        error_def = get_error_definition(self.error_code)

        debug_info = None
        if include_debug:
            debug_info = ErrorDebugInfo(
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id=self.request_id,
                function=self.function_name,
                file=self.file_name,
                line=self.line_number,
                user_id=self.user_id,
                additional_context=self.context,
            )

        # Determine message - use detail if it's a string, otherwise use default message
        message = error_def.message.plain
        details = self.context if self.context else None

        if self.detail:
            if isinstance(self.detail, str):
                message = self.detail
            elif isinstance(self.detail, dict):
                # If detail is a dict, use it as details and extract message if present
                details = self.detail
                if "message" in self.detail and isinstance(self.detail["message"], str):
                    message = self.detail["message"]

        return ErrorResponse(
            error_code=self.error_code,
            message=message,
            details=details,
            severity=error_def.severity,
            category=error_def.category,
            retry_after=error_def.retry_after,
            documentation_url=error_def.documentation_url,
            debug=debug_info,
        )


# ============================================================================
# AUTHENTICATION EXCEPTIONS (401)
# ============================================================================


class UnauthorizedException(ComputorException):
    """Authentication required - 401"""

    def __init__(
        self,
        error_code: str = "AUTH_001",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_401_UNAUTHORIZED


class BasicAuthException(ComputorException):
    """Basic authentication failed - 401 with WWW-Authenticate header"""

    def __init__(
        self,
        error_code: str = "AUTH_002",
        detail: Any = None,
        **kwargs,
    ):
        headers = {"WWW-Authenticate": "Basic"}
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_401_UNAUTHORIZED


class TokenExpiredException(ComputorException):
    """Authentication token expired - 401"""

    def __init__(
        self,
        error_code: str = "AUTH_003",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_401_UNAUTHORIZED


class SSOAuthException(ComputorException):
    """SSO authentication failed - 401"""

    def __init__(
        self,
        error_code: str = "AUTH_004",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_401_UNAUTHORIZED


# ============================================================================
# AUTHORIZATION EXCEPTIONS (403)
# ============================================================================


class ForbiddenException(ComputorException):
    """Insufficient permissions - 403"""

    def __init__(
        self,
        error_code: str = "AUTHZ_001",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_403_FORBIDDEN


class AdminRequiredException(ComputorException):
    """Admin access required - 403"""

    def __init__(
        self,
        error_code: str = "AUTHZ_002",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_403_FORBIDDEN


class CourseAccessDeniedException(ComputorException):
    """Course access denied - 403"""

    def __init__(
        self,
        error_code: str = "AUTHZ_003",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_403_FORBIDDEN


class InsufficientCourseRoleException(ComputorException):
    """Insufficient course role - 403"""

    def __init__(
        self,
        error_code: str = "AUTHZ_004",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        required_role: Optional[str] = None,
        **kwargs,
    ):
        if required_role:
            if "context" not in kwargs:
                kwargs["context"] = {}
            kwargs["context"]["required_role"] = required_role
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_403_FORBIDDEN


# ============================================================================
# VALIDATION EXCEPTIONS (400)
# ============================================================================


class BadRequestException(ComputorException):
    """Invalid request data - 400"""

    def __init__(
        self,
        error_code: str = "VAL_001",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_400_BAD_REQUEST


class MissingFieldException(ComputorException):
    """Required field missing - 400"""

    def __init__(
        self,
        field_name: str,
        error_code: str = "VAL_002",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        if "context" not in kwargs:
            kwargs["context"] = {}
        kwargs["context"]["field_name"] = field_name
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_400_BAD_REQUEST


class InvalidFieldFormatException(ComputorException):
    """Invalid field format - 400"""

    def __init__(
        self,
        field_name: str,
        expected_format: str,
        error_code: str = "VAL_003",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        if "context" not in kwargs:
            kwargs["context"] = {}
        kwargs["context"]["field_name"] = field_name
        kwargs["context"]["expected_format"] = expected_format
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_400_BAD_REQUEST


class InvalidFileUploadException(ComputorException):
    """Invalid file upload - 400"""

    def __init__(
        self,
        error_code: str = "VAL_004",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        max_size: Optional[str] = None,
        **kwargs,
    ):
        if max_size:
            if "context" not in kwargs:
                kwargs["context"] = {}
            kwargs["context"]["max_size"] = max_size
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_400_BAD_REQUEST


# ============================================================================
# NOT FOUND EXCEPTIONS (404)
# ============================================================================


class NotFoundException(ComputorException):
    """Resource not found - 404"""

    def __init__(
        self,
        error_code: str = "NF_001",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_404_NOT_FOUND


class UserNotFoundException(ComputorException):
    """User not found - 404"""

    def __init__(
        self,
        error_code: str = "NF_002",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_404_NOT_FOUND


class CourseNotFoundException(ComputorException):
    """Course not found - 404"""

    def __init__(
        self,
        error_code: str = "NF_003",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_404_NOT_FOUND


class EndpointNotFoundException(ComputorException):
    """Endpoint not found - 404"""

    def __init__(
        self,
        error_code: str = "NF_004",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_404_NOT_FOUND


# ============================================================================
# CONFLICT EXCEPTIONS (409)
# ============================================================================


class ConflictException(ComputorException):
    """Resource conflict - 409"""

    def __init__(
        self,
        error_code: str = "CONFLICT_001",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_409_CONFLICT


class ConcurrentModificationException(ComputorException):
    """Concurrent modification detected - 409"""

    def __init__(
        self,
        error_code: str = "CONFLICT_002",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_409_CONFLICT


# ============================================================================
# RATE LIMITING EXCEPTIONS (429)
# ============================================================================


class RateLimitException(ComputorException):
    """Rate limit exceeded - 429"""

    def __init__(
        self,
        error_code: str = "RATE_001",
        detail: Any = None,
        retry_after: int = 60,
        **kwargs,
    ):
        headers = {"Retry-After": str(retry_after)}
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_429_TOO_MANY_REQUESTS


# ============================================================================
# EXTERNAL SERVICE EXCEPTIONS (502, 503)
# ============================================================================


class GitLabServiceException(ComputorException):
    """GitLab service unavailable - 503"""

    def __init__(
        self,
        error_code: str = "EXT_001",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class GitLabAuthException(ComputorException):
    """GitLab authentication failed - 502"""

    def __init__(
        self,
        error_code: str = "EXT_002",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_502_BAD_GATEWAY


class MinIOServiceException(ComputorException):
    """MinIO service unavailable - 503"""

    def __init__(
        self,
        error_code: str = "EXT_003",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class TemporalServiceException(ComputorException):
    """Temporal service unavailable - 503"""

    def __init__(
        self,
        error_code: str = "EXT_004",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_503_SERVICE_UNAVAILABLE


# ============================================================================
# DATABASE EXCEPTIONS (500, 503)
# ============================================================================


class DatabaseConnectionException(ComputorException):
    """Database connection failed - 503"""

    def __init__(
        self,
        error_code: str = "DB_001",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class DatabaseQueryException(ComputorException):
    """Database query failed - 500"""

    def __init__(
        self,
        error_code: str = "DB_002",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class DatabaseTransactionException(ComputorException):
    """Database transaction failed - 500"""

    def __init__(
        self,
        error_code: str = "DB_003",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


# ============================================================================
# INTERNAL SERVER EXCEPTIONS (500)
# ============================================================================


class InternalServerException(ComputorException):
    """Internal server error - 500"""

    def __init__(
        self,
        error_code: str = "INT_001",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class ConfigurationException(ComputorException):
    """Configuration error - 500"""

    def __init__(
        self,
        error_code: str = "INT_002",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


# ============================================================================
# NOT IMPLEMENTED EXCEPTIONS (501)
# ============================================================================


class NotImplementedException(ComputorException):
    """Feature not implemented - 501"""

    def __init__(
        self,
        error_code: str = "NIMPL_001",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_501_NOT_IMPLEMENTED


# ============================================================================
# LEGACY COMPATIBILITY - DEPRECATED
# ============================================================================


class ServiceUnavailableException(ComputorException):
    """
    Legacy exception - use specific service exceptions instead.

    DEPRECATED: Use GitLabServiceException, MinIOServiceException, etc.
    """

    def __init__(
        self,
        error_code: str = "INT_001",
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(error_code=error_code, detail=detail, headers=headers, **kwargs)
        self.status_code = status.HTTP_503_SERVICE_UNAVAILABLE


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def response_to_http_exception(status_code: int, details: dict) -> Optional[ComputorException]:
    """
    Convert HTTP status code and details to appropriate exception.

    DEPRECATED: Use specific exception classes directly.

    Args:
        status_code: HTTP status code
        details: Error details dictionary

    Returns:
        Appropriate ComputorException subclass or None
    """
    if status_code == status.HTTP_404_NOT_FOUND:
        return NotFoundException(detail=details)
    elif status_code == status.HTTP_403_FORBIDDEN:
        return ForbiddenException(detail=details)
    elif status_code == status.HTTP_400_BAD_REQUEST:
        return BadRequestException(detail=details)
    elif status_code == status.HTTP_401_UNAUTHORIZED:
        return UnauthorizedException(detail=details)
    elif status_code == status.HTTP_501_NOT_IMPLEMENTED:
        return NotImplementedException(detail=details)
    elif status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        return InternalServerException(detail=details)
    elif status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        return ServiceUnavailableException(detail=details)
    else:
        return None
