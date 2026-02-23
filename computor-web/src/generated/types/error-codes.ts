/**
 * Auto-generated error code definitions
 *
 * DO NOT EDIT MANUALLY
 * Generated at: 2026-02-23T14:11:50.421886
 *
 * To regenerate: bash generate_error_codes.sh
 */

// ============================================================================
// Error Categories and Severities
// ============================================================================

export enum ErrorCategory {
  AUTHENTICATION = "authentication",
  AUTHORIZATION = "authorization",
  VALIDATION = "validation",
  NOT_FOUND = "not_found",
  CONFLICT = "conflict",
  RATE_LIMIT = "rate_limit",
  EXTERNAL_SERVICE = "external_service",
  DATABASE = "database",
  INTERNAL = "internal",
  NOT_IMPLEMENTED = "not_implemented",
}

export enum ErrorSeverity {
  INFO = "info",
  WARNING = "warning",
  ERROR = "error",
  CRITICAL = "critical",
}

// ============================================================================
// Error Response Interface
// ============================================================================

export interface ErrorDebugInfo {
  timestamp: string;
  request_id?: string;
  function?: string;
  file?: string;
  line?: number;
  user_id?: string;
  additional_context?: Record<string, any>;
}

export interface ErrorResponse {
  error_code: string;
  message: string;
  details?: any;
  severity: ErrorSeverity;
  category: ErrorCategory;
  retry_after?: number;
  documentation_url?: string;
  debug?: ErrorDebugInfo;
}

// ============================================================================
// Error Code Constants
// ============================================================================

export const ErrorCodes = {
  AUTH_001: "AUTH_001", // Authentication Required
  AUTH_002: "AUTH_002", // Invalid Credentials
  AUTH_003: "AUTH_003", // Token Expired
  AUTH_004: "AUTH_004", // SSO Authentication Failed
  AUTHZ_001: "AUTHZ_001", // Insufficient Permissions
  AUTHZ_002: "AUTHZ_002", // Admin Access Required
  AUTHZ_003: "AUTHZ_003", // Course Access Denied
  AUTHZ_004: "AUTHZ_004", // Insufficient Course Role
  AUTHZ_005: "AUTHZ_005", // Role Escalation Denied
  VAL_001: "VAL_001", // Invalid Request Data
  VAL_002: "VAL_002", // Missing Required Field
  VAL_003: "VAL_003", // Invalid Field Format
  VAL_004: "VAL_004", // Invalid File Upload
  NF_001: "NF_001", // Resource Not Found
  NF_002: "NF_002", // User Not Found
  NF_003: "NF_003", // Course Not Found
  NF_004: "NF_004", // Endpoint Not Found
  CONFLICT_001: "CONFLICT_001", // Resource Already Exists
  CONFLICT_002: "CONFLICT_002", // Concurrent Modification
  RATE_001: "RATE_001", // Rate Limit Exceeded
  RATE_002: "RATE_002", // Login Rate Limit Exceeded
  RATE_003: "RATE_003", // Test Request Rate Limit Exceeded
  CONTENT_001: "CONTENT_001", // Course Content Not Found
  CONTENT_002: "CONTENT_002", // Content Type Not Configured
  CONTENT_003: "CONTENT_003", // Invalid Content Type Operation
  CONTENT_004: "CONTENT_004", // Example Not Found
  CONTENT_005: "CONTENT_005", // Example Version Not Found
  VERSION_001: "VERSION_001", // Example Version Already Exists
  DEPLOY_001: "DEPLOY_001", // Assignment Not Released
  DEPLOY_002: "DEPLOY_002", // Deployment Not Found
  DEPLOY_003: "DEPLOY_003", // Repository Not Configured
  DEPLOY_004: "DEPLOY_004", // Missing Deployment Information
  SUBMIT_001: "SUBMIT_001", // Submission Artifact Not Found
  SUBMIT_002: "SUBMIT_002", // Submission Group Not Found
  SUBMIT_003: "SUBMIT_003", // Test Already Running
  SUBMIT_004: "SUBMIT_004", // Maximum Test Runs Exceeded
  SUBMIT_005: "SUBMIT_005", // Execution Backend Not Configured
  SUBMIT_006: "SUBMIT_006", // Version Identifier Required
  SUBMIT_007: "SUBMIT_007", // Test Identifier Required
  SUBMIT_008: "SUBMIT_008", // Artifact Already Tested
  TASK_001: "TASK_001", // Task Not Found
  TASK_002: "TASK_002", // Task Submission Failed
  TASK_003: "TASK_003", // Unsupported Execution Backend
  TASK_004: "TASK_004", // Course Membership Not Found
  GITLAB_001: "GITLAB_001", // GitLab Not Configured
  GITLAB_002: "GITLAB_002", // GitLab Account Not Registered
  GITLAB_003: "GITLAB_003", // GitLab Token Mismatch
  GITLAB_004: "GITLAB_004", // GitLab Account Already Linked
  GITLAB_005: "GITLAB_005", // GitLab Token Required
  GITLAB_006: "GITLAB_006", // GitLab Token Invalid
  GITLAB_007: "GITLAB_007", // GitLab API Unreachable
  GITLAB_008: "GITLAB_008", // Invalid GitLab Username
  EXT_001: "EXT_001", // GitLab Service Unavailable
  EXT_002: "EXT_002", // GitLab Authentication Failed
  EXT_003: "EXT_003", // MinIO Service Unavailable
  EXT_004: "EXT_004", // Temporal Service Unavailable
  EXT_005: "EXT_005", // Task Queue Unavailable
  DB_001: "DB_001", // Database Connection Failed
  DB_002: "DB_002", // Database Query Failed
  DB_003: "DB_003", // Transaction Failed
  INT_001: "INT_001", // Internal Server Error
  INT_002: "INT_002", // Configuration Error
  NIMPL_001: "NIMPL_001", // Feature Not Implemented
} as const;

export type ErrorCode = typeof ErrorCodes[keyof typeof ErrorCodes];

// ============================================================================
// Error Definitions
// ============================================================================

export interface ErrorDefinition {
  code: string;
  httpStatus: number;
  category: ErrorCategory;
  severity: ErrorSeverity;
  title: string;
  message: {
    plain: string;
    markdown?: string;
    html?: string;
  };
  retryAfter?: number;
  documentationUrl?: string;
}

export const ERROR_DEFINITIONS: Record<string, ErrorDefinition> = {
  AUTH_001: {
    code: "AUTH_001",
    httpStatus: 401,
    category: ErrorCategory.AUTHENTICATION,
    severity: ErrorSeverity.WARNING,
    title: "Authentication Required",
    message: {
      plain: "You must be authenticated to access this resource.",
      markdown: "**Authentication Required**\n\nYou must be authenticated to access this resource. Please log in and try again.",
      html: "<strong>Authentication Required</strong><p>You must be authenticated to access this resource. Please log in and try again.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/authentication",
  },
  AUTH_002: {
    code: "AUTH_002",
    httpStatus: 401,
    category: ErrorCategory.AUTHENTICATION,
    severity: ErrorSeverity.WARNING,
    title: "Invalid Credentials",
    message: {
      plain: "The username or password provided is incorrect.",
      markdown: "**Invalid Credentials**\n\nThe username or password you provided is incorrect. Please check your credentials and try again.",
      html: "<strong>Invalid Credentials</strong><p>The username or password you provided is incorrect. Please check your credentials and try again.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/authentication",
  },
  AUTH_003: {
    code: "AUTH_003",
    httpStatus: 401,
    category: ErrorCategory.AUTHENTICATION,
    severity: ErrorSeverity.WARNING,
    title: "Token Expired",
    message: {
      plain: "Your authentication token has expired. Please log in again.",
      markdown: "**Token Expired**\n\nYour authentication token has expired. Please log in again to continue.",
      html: "<strong>Token Expired</strong><p>Your authentication token has expired. Please log in again to continue.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/authentication#token-refresh",
  },
  AUTH_004: {
    code: "AUTH_004",
    httpStatus: 401,
    category: ErrorCategory.AUTHENTICATION,
    severity: ErrorSeverity.ERROR,
    title: "SSO Authentication Failed",
    message: {
      plain: "Single Sign-On authentication failed. Please try again or contact support.",
      markdown: "**SSO Authentication Failed**\n\nSingle Sign-On authentication failed. Please try again or contact support if the problem persists.",
      html: "<strong>SSO Authentication Failed</strong><p>Single Sign-On authentication failed. Please try again or contact support if the problem persists.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/authentication#sso",
  },
  AUTHZ_001: {
    code: "AUTHZ_001",
    httpStatus: 403,
    category: ErrorCategory.AUTHORIZATION,
    severity: ErrorSeverity.WARNING,
    title: "Insufficient Permissions",
    message: {
      plain: "You do not have permission to perform this action.",
      markdown: "**Insufficient Permissions**\n\nYou do not have the required permissions to perform this action.",
      html: "<strong>Insufficient Permissions</strong><p>You do not have the required permissions to perform this action.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/permissions",
  },
  AUTHZ_002: {
    code: "AUTHZ_002",
    httpStatus: 403,
    category: ErrorCategory.AUTHORIZATION,
    severity: ErrorSeverity.WARNING,
    title: "Admin Access Required",
    message: {
      plain: "This operation requires administrator privileges.",
      markdown: "**Admin Access Required**\n\nThis operation requires administrator privileges. Please contact your system administrator.",
      html: "<strong>Admin Access Required</strong><p>This operation requires administrator privileges. Please contact your system administrator.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/permissions#admin",
  },
  AUTHZ_003: {
    code: "AUTHZ_003",
    httpStatus: 403,
    category: ErrorCategory.AUTHORIZATION,
    severity: ErrorSeverity.WARNING,
    title: "Course Access Denied",
    message: {
      plain: "You do not have access to this course.",
      markdown: "**Course Access Denied**\n\nYou do not have access to this course. Please enroll or contact the course instructor.",
      html: "<strong>Course Access Denied</strong><p>You do not have access to this course. Please enroll or contact the course instructor.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/courses#enrollment",
  },
  AUTHZ_004: {
    code: "AUTHZ_004",
    httpStatus: 403,
    category: ErrorCategory.AUTHORIZATION,
    severity: ErrorSeverity.WARNING,
    title: "Insufficient Course Role",
    message: {
      plain: "Your course role is insufficient for this operation.",
      markdown: "**Insufficient Course Role**\n\nYour current role in this course does not allow this operation. Required role: {required_role}.",
      html: "<strong>Insufficient Course Role</strong><p>Your current role in this course does not allow this operation. Required role: <code>{required_role}</code>.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/permissions#course-roles",
  },
  AUTHZ_005: {
    code: "AUTHZ_005",
    httpStatus: 403,
    category: ErrorCategory.AUTHORIZATION,
    severity: ErrorSeverity.ERROR,
    title: "Role Escalation Denied",
    message: {
      plain: "You cannot assign a role higher than your own.",
      markdown: "**Role Escalation Denied**\n\nYou cannot assign the role '{target_role}'. Your role '{user_role}' can only assign roles at or below your privilege level.",
      html: "<strong>Role Escalation Denied</strong><p>You cannot assign the role <code>{target_role}</code>. Your role <code>{user_role}</code> can only assign roles at or below your privilege level.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/permissions#role-assignment",
  },
  VAL_001: {
    code: "VAL_001",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "Invalid Request Data",
    message: {
      plain: "The request data is invalid or malformed.",
      markdown: "**Invalid Request Data**\n\nThe request data you provided is invalid or malformed. Please check your input and try again.",
      html: "<strong>Invalid Request Data</strong><p>The request data you provided is invalid or malformed. Please check your input and try again.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/validation",
  },
  VAL_002: {
    code: "VAL_002",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "Missing Required Field",
    message: {
      plain: "A required field is missing from the request.",
      markdown: "**Missing Required Field**\n\nA required field is missing from your request: `{field_name}`.",
      html: "<strong>Missing Required Field</strong><p>A required field is missing from your request: <code>{field_name}</code>.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/validation",
  },
  VAL_003: {
    code: "VAL_003",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "Invalid Field Format",
    message: {
      plain: "A field has an invalid format.",
      markdown: "**Invalid Field Format**\n\nThe field `{field_name}` has an invalid format. Expected: {expected_format}.",
      html: "<strong>Invalid Field Format</strong><p>The field <code>{field_name}</code> has an invalid format. Expected: <code>{expected_format}</code>.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/validation",
  },
  VAL_004: {
    code: "VAL_004",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "Invalid File Upload",
    message: {
      plain: "The uploaded file is invalid or exceeds size limits.",
      markdown: "**Invalid File Upload**\n\nThe uploaded file is invalid or exceeds size limits. Maximum size: {max_size}.",
      html: "<strong>Invalid File Upload</strong><p>The uploaded file is invalid or exceeds size limits. Maximum size: <code>{max_size}</code>.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/file-uploads",
  },
  NF_001: {
    code: "NF_001",
    httpStatus: 404,
    category: ErrorCategory.NOT_FOUND,
    severity: ErrorSeverity.INFO,
    title: "Resource Not Found",
    message: {
      plain: "The requested resource was not found.",
      markdown: "**Resource Not Found**\n\nThe requested resource was not found. It may have been deleted or the URL is incorrect.",
      html: "<strong>Resource Not Found</strong><p>The requested resource was not found. It may have been deleted or the URL is incorrect.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/resources",
  },
  NF_002: {
    code: "NF_002",
    httpStatus: 404,
    category: ErrorCategory.NOT_FOUND,
    severity: ErrorSeverity.INFO,
    title: "User Not Found",
    message: {
      plain: "The specified user was not found.",
      markdown: "**User Not Found**\n\nThe specified user was not found in the system.",
      html: "<strong>User Not Found</strong><p>The specified user was not found in the system.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/users",
  },
  NF_003: {
    code: "NF_003",
    httpStatus: 404,
    category: ErrorCategory.NOT_FOUND,
    severity: ErrorSeverity.INFO,
    title: "Course Not Found",
    message: {
      plain: "The specified course was not found.",
      markdown: "**Course Not Found**\n\nThe specified course was not found or you do not have permission to access it.",
      html: "<strong>Course Not Found</strong><p>The specified course was not found or you do not have permission to access it.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/courses",
  },
  NF_004: {
    code: "NF_004",
    httpStatus: 404,
    category: ErrorCategory.NOT_FOUND,
    severity: ErrorSeverity.INFO,
    title: "Endpoint Not Found",
    message: {
      plain: "The requested API endpoint does not exist.",
      markdown: "**Endpoint Not Found**\n\nThe requested API endpoint does not exist. Please check the URL and API version.",
      html: "<strong>Endpoint Not Found</strong><p>The requested API endpoint does not exist. Please check the URL and API version.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api",
  },
  CONFLICT_001: {
    code: "CONFLICT_001",
    httpStatus: 409,
    category: ErrorCategory.CONFLICT,
    severity: ErrorSeverity.WARNING,
    title: "Resource Already Exists",
    message: {
      plain: "A resource with this identifier already exists.",
      markdown: "**Resource Already Exists**\n\nA resource with this identifier already exists. Use a different identifier or update the existing resource.",
      html: "<strong>Resource Already Exists</strong><p>A resource with this identifier already exists. Use a different identifier or update the existing resource.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/conflicts",
  },
  CONFLICT_002: {
    code: "CONFLICT_002",
    httpStatus: 409,
    category: ErrorCategory.CONFLICT,
    severity: ErrorSeverity.WARNING,
    title: "Concurrent Modification",
    message: {
      plain: "The resource was modified by another user. Please refresh and try again.",
      markdown: "**Concurrent Modification**\n\nThe resource was modified by another user. Please refresh and try again.",
      html: "<strong>Concurrent Modification</strong><p>The resource was modified by another user. Please refresh and try again.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/concurrency",
  },
  RATE_001: {
    code: "RATE_001",
    httpStatus: 429,
    category: ErrorCategory.RATE_LIMIT,
    severity: ErrorSeverity.WARNING,
    title: "Rate Limit Exceeded",
    message: {
      plain: "You have exceeded the rate limit. Please try again later.",
      markdown: "**Rate Limit Exceeded**\n\nYou have exceeded the rate limit. Please try again in {retry_after} seconds.",
      html: "<strong>Rate Limit Exceeded</strong><p>You have exceeded the rate limit. Please try again in <code>{retry_after}</code> seconds.</p>",
    },
    retryAfter: 60,
    documentationUrl: "/docs/api/rate-limits",
  },
  RATE_002: {
    code: "RATE_002",
    httpStatus: 429,
    category: ErrorCategory.RATE_LIMIT,
    severity: ErrorSeverity.WARNING,
    title: "Login Rate Limit Exceeded",
    message: {
      plain: "Too many login attempts. Please try again later.",
      markdown: "**Login Rate Limit Exceeded**\n\nToo many login attempts for this username. Please wait {retry_after} seconds before trying again.",
      html: "<strong>Login Rate Limit Exceeded</strong><p>Too many login attempts for this username. Please wait <code>{retry_after}</code> seconds before trying again.</p>",
    },
    retryAfter: 60,
    documentationUrl: "/docs/authentication#rate-limits",
  },
  RATE_003: {
    code: "RATE_003",
    httpStatus: 429,
    category: ErrorCategory.RATE_LIMIT,
    severity: ErrorSeverity.WARNING,
    title: "Test Request Rate Limit Exceeded",
    message: {
      plain: "Too many test requests. Please wait before submitting another test.",
      markdown: "**Test Request Rate Limit Exceeded**\n\nYou are submitting tests too quickly. Please wait {retry_after} second before trying again.",
      html: "<strong>Test Request Rate Limit Exceeded</strong><p>You are submitting tests too quickly. Please wait <code>{retry_after}</code> second before trying again.</p>",
    },
    retryAfter: 1,
    documentationUrl: "/docs/testing#rate-limits",
  },
  CONTENT_001: {
    code: "CONTENT_001",
    httpStatus: 404,
    category: ErrorCategory.NOT_FOUND,
    severity: ErrorSeverity.INFO,
    title: "Course Content Not Found",
    message: {
      plain: "The requested course content was not found.",
      markdown: "**Course Content Not Found**\n\nThe requested course content (assignment, exercise, etc.) was not found or you do not have permission to access it.",
      html: "<strong>Course Content Not Found</strong><p>The requested course content was not found or you do not have permission to access it.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/course-content",
  },
  CONTENT_002: {
    code: "CONTENT_002",
    httpStatus: 404,
    category: ErrorCategory.NOT_FOUND,
    severity: ErrorSeverity.WARNING,
    title: "Content Type Not Configured",
    message: {
      plain: "The content type for this assignment is not configured.",
      markdown: "**Content Type Not Configured**\n\nThe content type for this assignment is not properly configured. Please contact your instructor.",
      html: "<strong>Content Type Not Configured</strong><p>The content type for this assignment is not properly configured. Please contact your instructor.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/course-content#types",
  },
  CONTENT_003: {
    code: "CONTENT_003",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "Invalid Content Type Operation",
    message: {
      plain: "This operation is not valid for this content type.",
      markdown: "**Invalid Content Type Operation**\n\nThis operation cannot be performed on this content type. For example, you cannot assign examples to non-submittable content.",
      html: "<strong>Invalid Content Type Operation</strong><p>This operation cannot be performed on this content type.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/course-content#operations",
  },
  CONTENT_004: {
    code: "CONTENT_004",
    httpStatus: 404,
    category: ErrorCategory.NOT_FOUND,
    severity: ErrorSeverity.INFO,
    title: "Example Not Found",
    message: {
      plain: "The requested example was not found.",
      markdown: "**Example Not Found**\n\nThe requested example or example version was not found.",
      html: "<strong>Example Not Found</strong><p>The requested example or example version was not found.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/examples",
  },
  CONTENT_005: {
    code: "CONTENT_005",
    httpStatus: 404,
    category: ErrorCategory.NOT_FOUND,
    severity: ErrorSeverity.INFO,
    title: "Example Version Not Found",
    message: {
      plain: "The requested example version was not found.",
      markdown: "**Example Version Not Found**\n\nThe requested version of this example was not found. It may not exist or may have been deleted.",
      html: "<strong>Example Version Not Found</strong><p>The requested version of this example was not found.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/examples#versions",
  },
  VERSION_001: {
    code: "VERSION_001",
    httpStatus: 409,
    category: ErrorCategory.CONFLICT,
    severity: ErrorSeverity.WARNING,
    title: "Example Version Already Exists",
    message: {
      plain: "This version already exists for this example.",
      markdown: "**Example Version Already Exists**\n\nVersion `{version_tag}` already exists for this example. To update it, set `update_existing: true` in meta.yaml or use a different version tag.",
      html: "<strong>Example Version Already Exists</strong><p>Version <code>{version_tag}</code> already exists for this example. To update it, set <code>update_existing: true</code> in meta.yaml or use a different version tag.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/examples#version-management",
  },
  DEPLOY_001: {
    code: "DEPLOY_001",
    httpStatus: 404,
    category: ErrorCategory.NOT_FOUND,
    severity: ErrorSeverity.WARNING,
    title: "Assignment Not Released",
    message: {
      plain: "This assignment has not been released yet.",
      markdown: "**Assignment Not Released**\n\nThis assignment has not been released to students yet. Please wait for your instructor to release it.",
      html: "<strong>Assignment Not Released</strong><p>This assignment has not been released to students yet.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/assignments#deployment",
  },
  DEPLOY_002: {
    code: "DEPLOY_002",
    httpStatus: 404,
    category: ErrorCategory.NOT_FOUND,
    severity: ErrorSeverity.INFO,
    title: "Deployment Not Found",
    message: {
      plain: "The requested deployment was not found.",
      markdown: "**Deployment Not Found**\n\nThe requested deployment configuration was not found.",
      html: "<strong>Deployment Not Found</strong><p>The requested deployment configuration was not found.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/deployments",
  },
  DEPLOY_003: {
    code: "DEPLOY_003",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.ERROR,
    title: "Repository Not Configured",
    message: {
      plain: "The GitLab repository is not configured for this resource.",
      markdown: "**Repository Not Configured**\n\nThe GitLab repository has not been configured. Please contact your administrator.",
      html: "<strong>Repository Not Configured</strong><p>The GitLab repository has not been configured. Please contact your administrator.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/integrations/gitlab#configuration",
  },
  DEPLOY_004: {
    code: "DEPLOY_004",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "Missing Deployment Information",
    message: {
      plain: "Required deployment information is missing.",
      markdown: "**Missing Deployment Information**\n\nRequired deployment information (path, version, etc.) is missing. The assignment may not be properly configured.",
      html: "<strong>Missing Deployment Information</strong><p>Required deployment information is missing.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/assignments#deployment",
  },
  SUBMIT_001: {
    code: "SUBMIT_001",
    httpStatus: 404,
    category: ErrorCategory.NOT_FOUND,
    severity: ErrorSeverity.INFO,
    title: "Submission Artifact Not Found",
    message: {
      plain: "The requested submission artifact was not found.",
      markdown: "**Submission Artifact Not Found**\n\nThe requested submission artifact was not found. You may need to submit first.",
      html: "<strong>Submission Artifact Not Found</strong><p>The requested submission artifact was not found.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/submissions",
  },
  SUBMIT_002: {
    code: "SUBMIT_002",
    httpStatus: 404,
    category: ErrorCategory.NOT_FOUND,
    severity: ErrorSeverity.INFO,
    title: "Submission Group Not Found",
    message: {
      plain: "The requested submission group was not found.",
      markdown: "**Submission Group Not Found**\n\nThe requested submission group was not found or you do not have access to it.",
      html: "<strong>Submission Group Not Found</strong><p>The requested submission group was not found or you do not have access to it.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/assignments#groups",
  },
  SUBMIT_003: {
    code: "SUBMIT_003",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "Test Already Running",
    message: {
      plain: "A test is already running for this submission.",
      markdown: "**Test Already Running**\n\nA test is already running for this submission. Please wait for it to complete before starting another test.",
      html: "<strong>Test Already Running</strong><p>A test is already running for this submission.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/testing#status",
  },
  SUBMIT_004: {
    code: "SUBMIT_004",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "Maximum Test Runs Exceeded",
    message: {
      plain: "You have reached the maximum number of test runs for this submission.",
      markdown: "**Maximum Test Runs Exceeded**\n\nYou have reached the maximum number of test runs allowed for this submission.",
      html: "<strong>Maximum Test Runs Exceeded</strong><p>You have reached the maximum number of test runs allowed.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/testing#limits",
  },
  SUBMIT_005: {
    code: "SUBMIT_005",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "Execution Backend Not Configured",
    message: {
      plain: "The execution backend for this assignment is not configured.",
      markdown: "**Execution Backend Not Configured**\n\nThe execution backend for this assignment is not properly configured. Please contact your instructor.",
      html: "<strong>Execution Backend Not Configured</strong><p>The execution backend is not configured.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/testing#backends",
  },
  SUBMIT_006: {
    code: "SUBMIT_006",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "Version Identifier Required",
    message: {
      plain: "A version identifier (commit) is required for testing.",
      markdown: "**Version Identifier Required**\n\nA version identifier (commit hash) is required to test your submission. Please ensure your submission includes version information.",
      html: "<strong>Version Identifier Required</strong><p>A version identifier is required for testing.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/testing#versioning",
  },
  SUBMIT_007: {
    code: "SUBMIT_007",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "Test Identifier Required",
    message: {
      plain: "You must provide either an artifact ID or submission group ID to test.",
      markdown: "**Test Identifier Required**\n\nYou must provide either an artifact ID or submission group ID to identify what to test.",
      html: "<strong>Test Identifier Required</strong><p>You must provide an identifier for what to test.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/testing",
  },
  SUBMIT_008: {
    code: "SUBMIT_008",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "Artifact Already Tested",
    message: {
      plain: "You have already tested this artifact. Multiple tests are not allowed unless the previous test crashed or was cancelled.",
      markdown: "**Artifact Already Tested**\n\nYou have already successfully tested this artifact. Multiple tests are not allowed unless the previous test crashed or was cancelled.",
      html: "<strong>Artifact Already Tested</strong><p>You have already tested this artifact. Multiple tests are not allowed unless the previous test crashed or was cancelled.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/testing#duplicate-tests",
  },
  TASK_001: {
    code: "TASK_001",
    httpStatus: 404,
    category: ErrorCategory.NOT_FOUND,
    severity: ErrorSeverity.INFO,
    title: "Task Not Found",
    message: {
      plain: "The requested task execution was not found.",
      markdown: "**Task Not Found**\n\nThe requested task execution was not found or you do not have permission to view it.",
      html: "<strong>Task Not Found</strong><p>The requested task execution was not found.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/api/tasks",
  },
  TASK_002: {
    code: "TASK_002",
    httpStatus: 500,
    category: ErrorCategory.INTERNAL,
    severity: ErrorSeverity.ERROR,
    title: "Task Submission Failed",
    message: {
      plain: "Failed to submit the task for execution.",
      markdown: "**Task Submission Failed**\n\nFailed to submit the task to the execution system. Please try again or contact support.",
      html: "<strong>Task Submission Failed</strong><p>Failed to submit the task for execution.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/workflows#troubleshooting",
  },
  TASK_003: {
    code: "TASK_003",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "Unsupported Execution Backend",
    message: {
      plain: "The execution backend type is not supported.",
      markdown: "**Unsupported Execution Backend**\n\nThe execution backend type configured for this assignment is not supported.",
      html: "<strong>Unsupported Execution Backend</strong><p>The execution backend type is not supported.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/testing#backends",
  },
  TASK_004: {
    code: "TASK_004",
    httpStatus: 404,
    category: ErrorCategory.NOT_FOUND,
    severity: ErrorSeverity.INFO,
    title: "Course Membership Not Found",
    message: {
      plain: "You are not a member of this course.",
      markdown: "**Course Membership Not Found**\n\nYou are not enrolled as a member of this course.",
      html: "<strong>Course Membership Not Found</strong><p>You are not enrolled in this course.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/courses#enrollment",
  },
  GITLAB_001: {
    code: "GITLAB_001",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "GitLab Not Configured",
    message: {
      plain: "GitLab integration is not configured for this course.",
      markdown: "**GitLab Not Configured**\n\nGitLab integration has not been set up for this course. Please contact your instructor.",
      html: "<strong>GitLab Not Configured</strong><p>GitLab integration has not been set up for this course. Please contact your instructor.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/integrations/gitlab",
  },
  GITLAB_002: {
    code: "GITLAB_002",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.INFO,
    title: "GitLab Account Not Registered",
    message: {
      plain: "You have not registered your GitLab account for this course.",
      markdown: "**GitLab Account Not Registered**\n\nYou need to register your GitLab account to access course repositories. Please register via `/user/courses/{course_id}/register`.",
      html: "<strong>GitLab Account Not Registered</strong><p>You need to register your GitLab account to access course repositories.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/integrations/gitlab#registration",
  },
  GITLAB_003: {
    code: "GITLAB_003",
    httpStatus: 401,
    category: ErrorCategory.AUTHENTICATION,
    severity: ErrorSeverity.WARNING,
    title: "GitLab Token Mismatch",
    message: {
      plain: "The GitLab access token does not match your registered account.",
      markdown: "**GitLab Token Mismatch**\n\nThe access token you provided belongs to GitLab user `{actual_username}`, but your registered account is `{expected_username}`.",
      html: "<strong>GitLab Token Mismatch</strong><p>The access token belongs to a different GitLab user than your registered account.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/integrations/gitlab#tokens",
  },
  GITLAB_004: {
    code: "GITLAB_004",
    httpStatus: 409,
    category: ErrorCategory.CONFLICT,
    severity: ErrorSeverity.WARNING,
    title: "GitLab Account Already Linked",
    message: {
      plain: "This GitLab username is already linked to another user.",
      markdown: "**GitLab Account Already Linked**\n\nThe GitLab username `{username}` is already linked to another user account in this course.",
      html: "<strong>GitLab Account Already Linked</strong><p>This GitLab username is already linked to another user account.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/integrations/gitlab#registration",
  },
  GITLAB_005: {
    code: "GITLAB_005",
    httpStatus: 401,
    category: ErrorCategory.AUTHENTICATION,
    severity: ErrorSeverity.WARNING,
    title: "GitLab Token Required",
    message: {
      plain: "A GitLab personal access token is required for this operation.",
      markdown: "**GitLab Token Required**\n\nPlease provide your GitLab personal access token to register or validate your account. The token must have `api` scope.",
      html: "<strong>GitLab Token Required</strong><p>Please provide your GitLab personal access token with <code>api</code> scope.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/integrations/gitlab#tokens",
  },
  GITLAB_006: {
    code: "GITLAB_006",
    httpStatus: 502,
    category: ErrorCategory.EXTERNAL_SERVICE,
    severity: ErrorSeverity.ERROR,
    title: "GitLab Token Invalid",
    message: {
      plain: "The GitLab access token is invalid or has been revoked.",
      markdown: "**GitLab Token Invalid**\n\nThe GitLab access token you provided is invalid, expired, or has been revoked. Please generate a new token with `api` scope.",
      html: "<strong>GitLab Token Invalid</strong><p>The GitLab access token is invalid, expired, or revoked. Please generate a new token.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/integrations/gitlab#tokens",
  },
  GITLAB_007: {
    code: "GITLAB_007",
    httpStatus: 503,
    category: ErrorCategory.EXTERNAL_SERVICE,
    severity: ErrorSeverity.ERROR,
    title: "GitLab API Unreachable",
    message: {
      plain: "Unable to connect to GitLab API. Please try again later.",
      markdown: "**GitLab API Unreachable**\n\nUnable to connect to the GitLab API to verify your account. Please try again later.",
      html: "<strong>GitLab API Unreachable</strong><p>Unable to connect to GitLab. Please try again later.</p>",
    },
    retryAfter: 60,
    documentationUrl: "/docs/integrations/gitlab",
  },
  GITLAB_008: {
    code: "GITLAB_008",
    httpStatus: 400,
    category: ErrorCategory.VALIDATION,
    severity: ErrorSeverity.WARNING,
    title: "Invalid GitLab Username",
    message: {
      plain: "The GitLab username format is invalid.",
      markdown: "**Invalid GitLab Username**\n\nThe provided GitLab username is empty or has invalid format. Please provide a valid GitLab username.",
      html: "<strong>Invalid GitLab Username</strong><p>Please provide a valid GitLab username.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/integrations/gitlab#registration",
  },
  EXT_001: {
    code: "EXT_001",
    httpStatus: 503,
    category: ErrorCategory.EXTERNAL_SERVICE,
    severity: ErrorSeverity.ERROR,
    title: "GitLab Service Unavailable",
    message: {
      plain: "GitLab service is temporarily unavailable.",
      markdown: "**GitLab Service Unavailable**\n\nThe GitLab service is temporarily unavailable. Please try again later.",
      html: "<strong>GitLab Service Unavailable</strong><p>The GitLab service is temporarily unavailable. Please try again later.</p>",
    },
    retryAfter: 300,
    documentationUrl: "/docs/integrations/gitlab",
  },
  EXT_002: {
    code: "EXT_002",
    httpStatus: 502,
    category: ErrorCategory.EXTERNAL_SERVICE,
    severity: ErrorSeverity.ERROR,
    title: "GitLab Authentication Failed",
    message: {
      plain: "Failed to authenticate with GitLab.",
      markdown: "**GitLab Authentication Failed**\n\nFailed to authenticate with GitLab. Please check API token configuration.",
      html: "<strong>GitLab Authentication Failed</strong><p>Failed to authenticate with GitLab. Please check API token configuration.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/integrations/gitlab#authentication",
  },
  EXT_003: {
    code: "EXT_003",
    httpStatus: 503,
    category: ErrorCategory.EXTERNAL_SERVICE,
    severity: ErrorSeverity.ERROR,
    title: "MinIO Service Unavailable",
    message: {
      plain: "Object storage service is temporarily unavailable.",
      markdown: "**MinIO Service Unavailable**\n\nThe object storage service is temporarily unavailable. Please try again later.",
      html: "<strong>MinIO Service Unavailable</strong><p>The object storage service is temporarily unavailable. Please try again later.</p>",
    },
    retryAfter: 60,
    documentationUrl: "/docs/storage",
  },
  EXT_004: {
    code: "EXT_004",
    httpStatus: 503,
    category: ErrorCategory.EXTERNAL_SERVICE,
    severity: ErrorSeverity.ERROR,
    title: "Temporal Service Unavailable",
    message: {
      plain: "Workflow service is temporarily unavailable.",
      markdown: "**Temporal Service Unavailable**\n\nThe workflow orchestration service is temporarily unavailable. Please try again later.",
      html: "<strong>Temporal Service Unavailable</strong><p>The workflow orchestration service is temporarily unavailable. Please try again later.</p>",
    },
    retryAfter: 120,
    documentationUrl: "/docs/workflows",
  },
  EXT_005: {
    code: "EXT_005",
    httpStatus: 503,
    category: ErrorCategory.EXTERNAL_SERVICE,
    severity: ErrorSeverity.ERROR,
    title: "Task Queue Unavailable",
    message: {
      plain: "No worker available for the specified task queue.",
      markdown: "**Task Queue Unavailable**\n\nNo worker is available to process tasks on the specified queue. The testing service may be misconfigured or the worker is not running.",
      html: "<strong>Task Queue Unavailable</strong><p>No worker is available to process tasks on the specified queue. The testing service may be misconfigured or the worker is not running.</p>",
    },
    retryAfter: 120,
    documentationUrl: "/docs/testing-services",
  },
  DB_001: {
    code: "DB_001",
    httpStatus: 503,
    category: ErrorCategory.DATABASE,
    severity: ErrorSeverity.CRITICAL,
    title: "Database Connection Failed",
    message: {
      plain: "Unable to connect to the database.",
      markdown: "**Database Connection Failed**\n\nUnable to connect to the database. The service is temporarily unavailable.",
      html: "<strong>Database Connection Failed</strong><p>Unable to connect to the database. The service is temporarily unavailable.</p>",
    },
    retryAfter: 120,
    documentationUrl: "/docs/database",
  },
  DB_002: {
    code: "DB_002",
    httpStatus: 500,
    category: ErrorCategory.DATABASE,
    severity: ErrorSeverity.ERROR,
    title: "Database Query Failed",
    message: {
      plain: "A database query failed. Please try again.",
      markdown: "**Database Query Failed**\n\nA database query failed. Please try again or contact support if the problem persists.",
      html: "<strong>Database Query Failed</strong><p>A database query failed. Please try again or contact support if the problem persists.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/database",
  },
  DB_003: {
    code: "DB_003",
    httpStatus: 500,
    category: ErrorCategory.DATABASE,
    severity: ErrorSeverity.ERROR,
    title: "Transaction Failed",
    message: {
      plain: "Database transaction failed and was rolled back.",
      markdown: "**Transaction Failed**\n\nThe database transaction failed and was rolled back. No changes were made.",
      html: "<strong>Transaction Failed</strong><p>The database transaction failed and was rolled back. No changes were made.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/database#transactions",
  },
  INT_001: {
    code: "INT_001",
    httpStatus: 500,
    category: ErrorCategory.INTERNAL,
    severity: ErrorSeverity.CRITICAL,
    title: "Internal Server Error",
    message: {
      plain: "An unexpected error occurred. Please try again later.",
      markdown: "**Internal Server Error**\n\nAn unexpected error occurred. Please try again later or contact support.",
      html: "<strong>Internal Server Error</strong><p>An unexpected error occurred. Please try again later or contact support.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/support",
  },
  INT_002: {
    code: "INT_002",
    httpStatus: 500,
    category: ErrorCategory.INTERNAL,
    severity: ErrorSeverity.CRITICAL,
    title: "Configuration Error",
    message: {
      plain: "Server configuration error. Please contact administrator.",
      markdown: "**Configuration Error**\n\nA server configuration error occurred. Please contact your administrator.",
      html: "<strong>Configuration Error</strong><p>A server configuration error occurred. Please contact your administrator.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/configuration",
  },
  NIMPL_001: {
    code: "NIMPL_001",
    httpStatus: 501,
    category: ErrorCategory.NOT_IMPLEMENTED,
    severity: ErrorSeverity.INFO,
    title: "Feature Not Implemented",
    message: {
      plain: "This feature is not yet implemented.",
      markdown: "**Feature Not Implemented**\n\nThis feature is not yet implemented. Check the documentation for available alternatives.",
      html: "<strong>Feature Not Implemented</strong><p>This feature is not yet implemented. Check the documentation for available alternatives.</p>",
    },
    retryAfter: undefined,
    documentationUrl: "/docs/roadmap",
  }
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Get error definition by code
 */
export function getErrorDefinition(code: string): ErrorDefinition | undefined {
  return ERROR_DEFINITIONS[code];
}

/**
 * Get user-friendly error message
 */
export function getErrorMessage(error: ErrorResponse, format: "plain" | "markdown" | "html" = "plain"): string {
  const definition = getErrorDefinition(error.error_code);

  if (!definition) {
    return error.message;
  }

  // Use custom message if provided, otherwise use definition
  if (error.message) {
    return error.message;
  }

  const formatMessage = definition.message[format];
  return formatMessage || definition.message.plain;
}

/**
 * Check if error is retryable
 */
export function isRetryableError(error: ErrorResponse): boolean {
  const retryableCategories = [
    ErrorCategory.RATE_LIMIT,
    ErrorCategory.EXTERNAL_SERVICE,
    ErrorCategory.DATABASE,
  ];

  return retryableCategories.includes(error.category);
}

/**
 * Get retry delay in milliseconds
 */
export function getRetryDelay(error: ErrorResponse): number | undefined {
  if (!isRetryableError(error)) {
    return undefined;
  }

  if (error.retry_after) {
    return error.retry_after * 1000; // Convert seconds to milliseconds
  }

  // Default retry delays by category
  const defaultDelays: Record<ErrorCategory, number> = {
    [ErrorCategory.RATE_LIMIT]: 60000, // 1 minute
    [ErrorCategory.EXTERNAL_SERVICE]: 30000, // 30 seconds
    [ErrorCategory.DATABASE]: 5000, // 5 seconds
    [ErrorCategory.AUTHENTICATION]: 0,
    [ErrorCategory.AUTHORIZATION]: 0,
    [ErrorCategory.VALIDATION]: 0,
    [ErrorCategory.NOT_FOUND]: 0,
    [ErrorCategory.CONFLICT]: 0,
    [ErrorCategory.INTERNAL]: 0,
    [ErrorCategory.NOT_IMPLEMENTED]: 0,
  };

  return defaultDelays[error.category] || 0;
}

/**
 * Format error for display in UI
 */
export interface FormattedError {
  title: string;
  message: string;
  severity: ErrorSeverity;
  canRetry: boolean;
  retryDelay?: number;
  documentationUrl?: string;
}

export function formatErrorForDisplay(error: ErrorResponse): FormattedError {
  const definition = getErrorDefinition(error.error_code);

  return {
    title: definition?.title || "Error",
    message: getErrorMessage(error, "markdown"),
    severity: error.severity,
    canRetry: isRetryableError(error),
    retryDelay: getRetryDelay(error),
    documentationUrl: error.documentation_url || definition?.documentationUrl,
  };
}

/**
 * Get all errors by category
 */
export function getErrorsByCategory(category: ErrorCategory): ErrorDefinition[] {
  return Object.values(ERROR_DEFINITIONS).filter(
    (def) => def.category === category
  );
}

/**
 * Get all errors by HTTP status
 */
export function getErrorsByHttpStatus(httpStatus: number): ErrorDefinition[] {
  return Object.values(ERROR_DEFINITIONS).filter(
    (def) => def.httpStatus === httpStatus
  );
}
