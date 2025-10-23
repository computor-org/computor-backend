"""
Error handling package for Computor backend.

This package provides:
- Custom exception classes with error codes
- Error registry management
- FastAPI exception handlers
- Structured error responses

Usage:
    from computor_backend.exceptions import (
        NotFoundException,
        ForbiddenException,
        register_exception_handlers,
    )
"""

# Exception classes
from computor_backend.exceptions.exceptions import (
    # Base exception
    ComputorException,

    # Authentication exceptions (401)
    UnauthorizedException,
    BasicAuthException,
    TokenExpiredException,
    SSOAuthException,

    # Authorization exceptions (403)
    ForbiddenException,
    AdminRequiredException,
    CourseAccessDeniedException,
    InsufficientCourseRoleException,

    # Validation exceptions (400)
    BadRequestException,
    MissingFieldException,
    InvalidFieldFormatException,
    InvalidFileUploadException,

    # Not found exceptions (404)
    NotFoundException,
    UserNotFoundException,
    CourseNotFoundException,
    EndpointNotFoundException,

    # Conflict exceptions (409)
    ConflictException,
    ConcurrentModificationException,

    # Rate limiting exceptions (429)
    RateLimitException,

    # External service exceptions (502/503)
    GitLabServiceException,
    GitLabAuthException,
    MinIOServiceException,
    TemporalServiceException,

    # Database exceptions (500/503)
    DatabaseConnectionException,
    DatabaseQueryException,
    DatabaseTransactionException,

    # Internal server exceptions (500)
    InternalServerException,
    ConfigurationException,

    # Not implemented exceptions (501)
    NotImplementedException,

    # Legacy/deprecated
    ServiceUnavailableException,

    # Helper functions
    response_to_http_exception,
)

# Error registry functions
from computor_backend.exceptions.error_registry import (
    load_error_registry,
    get_error_definition,
    get_all_error_codes,
    get_errors_by_category,
    get_errors_by_http_status,
    get_registry_version,
    validate_error_registry,
)

# Exception handlers
from computor_backend.exceptions.error_handlers import (
    register_exception_handlers,
    computor_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)


__all__ = [
    # Base
    "ComputorException",

    # Authentication
    "UnauthorizedException",
    "BasicAuthException",
    "TokenExpiredException",
    "SSOAuthException",

    # Authorization
    "ForbiddenException",
    "AdminRequiredException",
    "CourseAccessDeniedException",
    "InsufficientCourseRoleException",

    # Validation
    "BadRequestException",
    "MissingFieldException",
    "InvalidFieldFormatException",
    "InvalidFileUploadException",

    # Not Found
    "NotFoundException",
    "UserNotFoundException",
    "CourseNotFoundException",
    "EndpointNotFoundException",

    # Conflict
    "ConflictException",
    "ConcurrentModificationException",

    # Rate Limiting
    "RateLimitException",

    # External Services
    "GitLabServiceException",
    "GitLabAuthException",
    "MinIOServiceException",
    "TemporalServiceException",

    # Database
    "DatabaseConnectionException",
    "DatabaseQueryException",
    "DatabaseTransactionException",

    # Internal
    "InternalServerException",
    "ConfigurationException",

    # Not Implemented
    "NotImplementedException",

    # Legacy
    "ServiceUnavailableException",

    # Helpers
    "response_to_http_exception",

    # Registry
    "load_error_registry",
    "get_error_definition",
    "get_all_error_codes",
    "get_errors_by_category",
    "get_errors_by_http_status",
    "get_registry_version",
    "validate_error_registry",

    # Handlers
    "register_exception_handlers",
    "computor_exception_handler",
    "validation_exception_handler",
    "http_exception_handler",
    "generic_exception_handler",
]
