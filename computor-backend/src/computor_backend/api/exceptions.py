"""
DEPRECATED: This module has been moved to computor_backend.exceptions

This file provides backward compatibility for existing imports.
Please update your imports to use the new location:

    from computor_backend.exceptions import NotFoundException, ForbiddenException

Instead of:

    from computor_backend.api.exceptions import NotFoundException, ForbiddenException
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from computor_backend.api.exceptions is deprecated. "
    "Use computor_backend.exceptions instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from the new location for backward compatibility
from computor_backend.exceptions.exceptions import *  # noqa: F401, F403

__all__ = [
    "ComputorException",
    "UnauthorizedException",
    "BasicAuthException",
    "TokenExpiredException",
    "SSOAuthException",
    "ForbiddenException",
    "AdminRequiredException",
    "CourseAccessDeniedException",
    "InsufficientCourseRoleException",
    "BadRequestException",
    "MissingFieldException",
    "InvalidFieldFormatException",
    "InvalidFileUploadException",
    "NotFoundException",
    "UserNotFoundException",
    "CourseNotFoundException",
    "EndpointNotFoundException",
    "ConflictException",
    "ConcurrentModificationException",
    "RateLimitException",
    "GitLabServiceException",
    "GitLabAuthException",
    "MinIOServiceException",
    "TemporalServiceException",
    "DatabaseConnectionException",
    "DatabaseQueryException",
    "DatabaseTransactionException",
    "InternalServerException",
    "ConfigurationException",
    "NotImplementedException",
    "ServiceUnavailableException",
    "response_to_http_exception",
]
