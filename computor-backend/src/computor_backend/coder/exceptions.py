"""
Custom exceptions for Coder integration.
"""

from typing import Any, Optional


class CoderError(Exception):
    """Base exception for Coder-related errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        detail: Optional[str] = None,
        response_data: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        self.response_data = response_data
        super().__init__(self.message)

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"(status: {self.status_code})")
        if self.detail:
            parts.append(f"- {self.detail}")
        return " ".join(parts)


class CoderAPIError(CoderError):
    """Raised when Coder API returns an error response."""

    pass


class CoderConnectionError(CoderError):
    """Raised when connection to Coder server fails."""

    def __init__(self, message: str = "Failed to connect to Coder server", **kwargs):
        super().__init__(message, **kwargs)


class CoderAuthenticationError(CoderError):
    """Raised when authentication with Coder fails."""

    def __init__(self, message: str = "Failed to authenticate with Coder", **kwargs):
        super().__init__(message, status_code=401, **kwargs)


class CoderNotFoundError(CoderError):
    """Raised when a requested resource is not found."""

    def __init__(self, resource_type: str, identifier: str, **kwargs):
        message = f"{resource_type} not found: {identifier}"
        super().__init__(message, status_code=404, **kwargs)
        self.resource_type = resource_type
        self.identifier = identifier


class CoderUserNotFoundError(CoderNotFoundError):
    """Raised when a user is not found."""

    def __init__(self, identifier: str, **kwargs):
        super().__init__("User", identifier, **kwargs)


class CoderWorkspaceNotFoundError(CoderNotFoundError):
    """Raised when a workspace is not found."""

    def __init__(self, identifier: str, **kwargs):
        super().__init__("Workspace", identifier, **kwargs)


class CoderTemplateNotFoundError(CoderNotFoundError):
    """Raised when a template is not found."""

    def __init__(self, identifier: str, **kwargs):
        super().__init__("Template", identifier, **kwargs)


class CoderConflictError(CoderError):
    """Raised when a resource already exists."""

    def __init__(self, resource_type: str, identifier: str, **kwargs):
        message = f"{resource_type} already exists: {identifier}"
        super().__init__(message, status_code=409, **kwargs)
        self.resource_type = resource_type
        self.identifier = identifier


class CoderUserExistsError(CoderConflictError):
    """Raised when trying to create a user that already exists."""

    def __init__(self, identifier: str, **kwargs):
        super().__init__("User", identifier, **kwargs)


class CoderWorkspaceExistsError(CoderConflictError):
    """Raised when trying to create a workspace that already exists."""

    def __init__(self, identifier: str, **kwargs):
        super().__init__("Workspace", identifier, **kwargs)


class CoderPermissionError(CoderError):
    """Raised when operation is not permitted."""

    def __init__(self, message: str = "Operation not permitted", **kwargs):
        super().__init__(message, status_code=403, **kwargs)


class CoderTimeoutError(CoderError):
    """Raised when an operation times out."""

    def __init__(self, operation: str, timeout: float, **kwargs):
        message = f"Operation '{operation}' timed out after {timeout}s"
        super().__init__(message, **kwargs)
        self.operation = operation
        self.timeout = timeout


class CoderWorkspaceActionError(CoderError):
    """Raised when a workspace action (start/stop/delete) fails."""

    def __init__(self, action: str, workspace: str, reason: Optional[str] = None, **kwargs):
        message = f"Failed to {action} workspace '{workspace}'"
        if reason:
            message += f": {reason}"
        super().__init__(message, **kwargs)
        self.action = action
        self.workspace = workspace


class CoderDisabledError(CoderError):
    """Raised when Coder integration is disabled."""

    def __init__(self):
        super().__init__("Coder integration is disabled", status_code=503)
