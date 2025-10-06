"""Exceptions for Computor client."""

from typing import Any, Dict, Optional


class ComputorClientError(Exception):
    """Base exception for all Computor client errors."""
    pass


class ComputorAPIError(ComputorClientError):
    """API returned an error response."""

    def __init__(
        self,
        status_code: int,
        message: str,
        detail: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.message = message
        self.detail = detail or {}
        super().__init__(f"[{status_code}] {message}")


class ComputorAuthenticationError(ComputorAPIError):
    """Authentication failed (401)."""

    def __init__(self, message: str = "Authentication failed", detail: Optional[Dict[str, Any]] = None):
        super().__init__(401, message, detail)


class ComputorAuthorizationError(ComputorAPIError):
    """Authorization failed - insufficient permissions (403)."""

    def __init__(self, message: str = "Insufficient permissions", detail: Optional[Dict[str, Any]] = None):
        super().__init__(403, message, detail)


class ComputorNotFoundError(ComputorAPIError):
    """Resource not found (404)."""

    def __init__(self, message: str = "Resource not found", detail: Optional[Dict[str, Any]] = None):
        super().__init__(404, message, detail)


class ComputorValidationError(ComputorAPIError):
    """Request validation failed (422)."""

    def __init__(self, message: str = "Validation error", detail: Optional[Dict[str, Any]] = None):
        super().__init__(422, message, detail)


class ComputorServerError(ComputorAPIError):
    """Server error (5xx)."""

    def __init__(self, status_code: int, message: str = "Server error", detail: Optional[Dict[str, Any]] = None):
        super().__init__(status_code, message, detail)


def raise_for_status(status_code: int, response_data: Any) -> None:
    """Raise appropriate exception based on status code."""

    if 200 <= status_code < 300:
        return  # Success, no exception

    # Extract message from response
    if isinstance(response_data, dict):
        message = response_data.get("detail", response_data.get("message", "Unknown error"))
        detail = response_data
    else:
        message = str(response_data)
        detail = {"detail": response_data}

    # Raise specific exception based on status code
    if status_code == 401:
        raise ComputorAuthenticationError(message, detail)
    elif status_code == 403:
        raise ComputorAuthorizationError(message, detail)
    elif status_code == 404:
        raise ComputorNotFoundError(message, detail)
    elif status_code == 422:
        raise ComputorValidationError(message, detail)
    elif 500 <= status_code < 600:
        raise ComputorServerError(status_code, message, detail)
    else:
        raise ComputorAPIError(status_code, message, detail)
