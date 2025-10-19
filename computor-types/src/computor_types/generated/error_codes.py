"""
Auto-generated error code constants

DO NOT EDIT MANUALLY
Generated at: 2025-10-20T00:51:42.129914

To regenerate: bash generate_error_codes.sh
"""

from enum import Enum


class ErrorCode(str, Enum):
    """Error code constants."""
    AUTH_001 = "AUTH_001"  # Authentication Required
    AUTH_002 = "AUTH_002"  # Invalid Credentials
    AUTH_003 = "AUTH_003"  # Token Expired
    AUTH_004 = "AUTH_004"  # SSO Authentication Failed
    AUTHZ_001 = "AUTHZ_001"  # Insufficient Permissions
    AUTHZ_002 = "AUTHZ_002"  # Admin Access Required
    AUTHZ_003 = "AUTHZ_003"  # Course Access Denied
    AUTHZ_004 = "AUTHZ_004"  # Insufficient Course Role
    VAL_001 = "VAL_001"  # Invalid Request Data
    VAL_002 = "VAL_002"  # Missing Required Field
    VAL_003 = "VAL_003"  # Invalid Field Format
    VAL_004 = "VAL_004"  # Invalid File Upload
    NF_001 = "NF_001"  # Resource Not Found
    NF_002 = "NF_002"  # User Not Found
    NF_003 = "NF_003"  # Course Not Found
    NF_004 = "NF_004"  # Endpoint Not Found
    CONFLICT_001 = "CONFLICT_001"  # Resource Already Exists
    CONFLICT_002 = "CONFLICT_002"  # Concurrent Modification
    RATE_001 = "RATE_001"  # Rate Limit Exceeded
    RATE_002 = "RATE_002"  # Login Rate Limit Exceeded
    RATE_003 = "RATE_003"  # Test Request Rate Limit Exceeded
    CONTENT_001 = "CONTENT_001"  # Course Content Not Found
    CONTENT_002 = "CONTENT_002"  # Content Type Not Configured
    CONTENT_003 = "CONTENT_003"  # Invalid Content Type Operation
    CONTENT_004 = "CONTENT_004"  # Example Not Found
    CONTENT_005 = "CONTENT_005"  # Example Version Not Found
    DEPLOY_001 = "DEPLOY_001"  # Assignment Not Released
    DEPLOY_002 = "DEPLOY_002"  # Deployment Not Found
    DEPLOY_003 = "DEPLOY_003"  # Repository Not Configured
    DEPLOY_004 = "DEPLOY_004"  # Missing Deployment Information
    SUBMIT_001 = "SUBMIT_001"  # Submission Artifact Not Found
    SUBMIT_002 = "SUBMIT_002"  # Submission Group Not Found
    SUBMIT_003 = "SUBMIT_003"  # Test Already Running
    SUBMIT_004 = "SUBMIT_004"  # Maximum Test Runs Exceeded
    SUBMIT_005 = "SUBMIT_005"  # Execution Backend Not Configured
    SUBMIT_006 = "SUBMIT_006"  # Version Identifier Required
    SUBMIT_007 = "SUBMIT_007"  # Test Identifier Required
    SUBMIT_008 = "SUBMIT_008"  # Artifact Already Tested
    TASK_001 = "TASK_001"  # Task Not Found
    TASK_002 = "TASK_002"  # Task Submission Failed
    TASK_003 = "TASK_003"  # Unsupported Execution Backend
    TASK_004 = "TASK_004"  # Course Membership Not Found
    EXT_001 = "EXT_001"  # GitLab Service Unavailable
    EXT_002 = "EXT_002"  # GitLab Authentication Failed
    EXT_003 = "EXT_003"  # MinIO Service Unavailable
    EXT_004 = "EXT_004"  # Temporal Service Unavailable
    DB_001 = "DB_001"  # Database Connection Failed
    DB_002 = "DB_002"  # Database Query Failed
    DB_003 = "DB_003"  # Transaction Failed
    INT_001 = "INT_001"  # Internal Server Error
    INT_002 = "INT_002"  # Configuration Error
    NIMPL_001 = "NIMPL_001"  # Feature Not Implemented


# Mapping of HTTP status codes to default error codes
HTTP_STATUS_TO_ERROR_CODE = {
    400: ErrorCode.VAL_001,
    401: ErrorCode.AUTH_001,
    403: ErrorCode.AUTHZ_001,
    404: ErrorCode.NF_001,
    409: ErrorCode.CONFLICT_001,
    429: ErrorCode.RATE_001,
    500: ErrorCode.TASK_002,
    501: ErrorCode.NIMPL_001,
    502: ErrorCode.EXT_002,
    503: ErrorCode.EXT_001,
}

# Mapping of error categories
ERROR_CATEGORIES = {
    ErrorCode.AUTH_001: "authentication",
    ErrorCode.AUTH_002: "authentication",
    ErrorCode.AUTH_003: "authentication",
    ErrorCode.AUTH_004: "authentication",
    ErrorCode.AUTHZ_001: "authorization",
    ErrorCode.AUTHZ_002: "authorization",
    ErrorCode.AUTHZ_003: "authorization",
    ErrorCode.AUTHZ_004: "authorization",
    ErrorCode.VAL_001: "validation",
    ErrorCode.VAL_002: "validation",
    ErrorCode.VAL_003: "validation",
    ErrorCode.VAL_004: "validation",
    ErrorCode.NF_001: "not_found",
    ErrorCode.NF_002: "not_found",
    ErrorCode.NF_003: "not_found",
    ErrorCode.NF_004: "not_found",
    ErrorCode.CONFLICT_001: "conflict",
    ErrorCode.CONFLICT_002: "conflict",
    ErrorCode.RATE_001: "rate_limit",
    ErrorCode.RATE_002: "rate_limit",
    ErrorCode.RATE_003: "rate_limit",
    ErrorCode.CONTENT_001: "not_found",
    ErrorCode.CONTENT_002: "not_found",
    ErrorCode.CONTENT_003: "validation",
    ErrorCode.CONTENT_004: "not_found",
    ErrorCode.CONTENT_005: "not_found",
    ErrorCode.DEPLOY_001: "not_found",
    ErrorCode.DEPLOY_002: "not_found",
    ErrorCode.DEPLOY_003: "validation",
    ErrorCode.DEPLOY_004: "validation",
    ErrorCode.SUBMIT_001: "not_found",
    ErrorCode.SUBMIT_002: "not_found",
    ErrorCode.SUBMIT_003: "validation",
    ErrorCode.SUBMIT_004: "validation",
    ErrorCode.SUBMIT_005: "validation",
    ErrorCode.SUBMIT_006: "validation",
    ErrorCode.SUBMIT_007: "validation",
    ErrorCode.SUBMIT_008: "validation",
    ErrorCode.TASK_001: "not_found",
    ErrorCode.TASK_002: "internal",
    ErrorCode.TASK_003: "validation",
    ErrorCode.TASK_004: "not_found",
    ErrorCode.EXT_001: "external_service",
    ErrorCode.EXT_002: "external_service",
    ErrorCode.EXT_003: "external_service",
    ErrorCode.EXT_004: "external_service",
    ErrorCode.DB_001: "database",
    ErrorCode.DB_002: "database",
    ErrorCode.DB_003: "database",
    ErrorCode.INT_001: "internal",
    ErrorCode.INT_002: "internal",
    ErrorCode.NIMPL_001: "not_implemented",
}
