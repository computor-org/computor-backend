"""
Error handling models and definitions for the Computor platform.

This module provides structured error handling with:
- Unique error codes for every exception
- Rich metadata for debugging
- Multi-format error messages (plain text, markdown, HTML)
- TypeScript generation support
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    RATE_LIMIT = "rate_limit"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    INTERNAL = "internal"
    NOT_IMPLEMENTED = "not_implemented"


class ErrorMessageFormat(BaseModel):
    """Multi-format error message."""
    plain: str = Field(..., description="Plain text error message")
    markdown: Optional[str] = Field(None, description="Markdown formatted message")
    html: Optional[str] = Field(None, description="HTML formatted message")


class ErrorDefinition(BaseModel):
    """Complete error definition from registry."""
    code: str = Field(..., description="Unique error code (e.g., AUTH_001)")
    http_status: int = Field(..., description="HTTP status code")
    category: ErrorCategory = Field(..., description="Error category")
    severity: ErrorSeverity = Field(..., description="Error severity")
    title: str = Field(..., description="Short error title")
    message: ErrorMessageFormat = Field(..., description="Error messages in multiple formats")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")
    documentation_url: Optional[str] = Field(None, description="Link to documentation")

    # Developer information
    internal_description: str = Field(..., description="Internal description for developers")
    affected_functions: list[str] = Field(default_factory=list, description="Functions that may raise this error")
    common_causes: list[str] = Field(default_factory=list, description="Common causes of this error")
    resolution_steps: list[str] = Field(default_factory=list, description="Steps to resolve the error")

    class Config:
        use_enum_values = True


class ErrorResponse(BaseModel):
    """Standard error response structure sent to clients."""
    error_code: str = Field(..., description="Unique error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Any] = Field(None, description="Additional error details")
    severity: ErrorSeverity = Field(..., description="Error severity")
    category: ErrorCategory = Field(..., description="Error category")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")
    documentation_url: Optional[str] = Field(None, description="Link to documentation")

    # Debug information (only in development mode)
    debug: Optional["ErrorDebugInfo"] = Field(None, description="Debug information (dev mode only)")

    class Config:
        use_enum_values = True


class ErrorDebugInfo(BaseModel):
    """Debug information included in development mode."""
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    request_id: Optional[str] = Field(None, description="Request trace ID")
    function: Optional[str] = Field(None, description="Function where error occurred")
    file: Optional[str] = Field(None, description="File where error occurred")
    line: Optional[int] = Field(None, description="Line number where error occurred")
    user_id: Optional[str] = Field(None, description="User ID if authenticated")
    additional_context: Optional[dict[str, Any]] = Field(None, description="Additional context")


class ErrorMetadata(BaseModel):
    """
    Metadata attached to exception instances for rich error handling.

    This is used internally when raising exceptions to provide context.
    """
    error_code: str = Field(..., description="Error code from registry")
    function_name: Optional[str] = Field(None, description="Function raising the error")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    user_id: Optional[str] = Field(None, description="User ID if available")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")

    # Override message fields if needed
    override_message: Optional[str] = Field(None, description="Override default message")
    override_details: Optional[Any] = Field(None, description="Override default details")


# Update ErrorResponse to avoid forward reference issues
ErrorResponse.model_rebuild()
