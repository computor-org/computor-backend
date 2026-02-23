# Error Code Reference

**Auto-generated documentation**
**Generated:** 2026-02-23 14:11:50
**Total errors:** 63

To regenerate: `bash generate_error_codes.sh`

---

## Table of Contents

- [Authentication](#authentication)
- [Authorization](#authorization)
- [Conflict](#conflict)
- [Database](#database)
- [External Service](#external-service)
- [Internal](#internal)
- [Not Found](#not-found)
- [Not Implemented](#not-implemented)
- [Rate Limit](#rate-limit)
- [Validation](#validation)

---

## Authentication

### AUTH_001 - Authentication Required

**HTTP Status:** `401`  
**Severity:** `warning`  
**Category:** `authentication`  
**Documentation:** [/docs/authentication](/docs/authentication)  

**Description:**  
User attempted to access a protected endpoint without valid authentication credentials

**User Message:**  
> You must be authenticated to access this resource.

**Affected Functions:**
- `get_current_principal`
- `verify_token`

**Common Causes:**
- Missing or invalid authentication token
- Expired session
- Token not included in request headers

**Resolution Steps:**
1. Ensure you are logged in
2. Check that the authentication token is included in the Authorization header
3. Verify the token has not expired

---

### AUTH_002 - Invalid Credentials

**HTTP Status:** `401`  
**Severity:** `warning`  
**Category:** `authentication`  
**Documentation:** [/docs/authentication](/docs/authentication)  

**Description:**  
User provided incorrect username or password during basic authentication

**User Message:**  
> The username or password provided is incorrect.

**Affected Functions:**
- `verify_basic_auth`
- `authenticate_user`

**Common Causes:**
- Incorrect password
- Username does not exist
- Account locked or disabled

**Resolution Steps:**
1. Verify your username and password
2. Check for typos in credentials
3. Contact administrator if account is locked

---

### AUTH_003 - Token Expired

**HTTP Status:** `401`  
**Severity:** `warning`  
**Category:** `authentication`  
**Documentation:** [/docs/authentication#token-refresh](/docs/authentication#token-refresh)  

**Description:**  
JWT or session token has expired and needs renewal

**User Message:**  
> Your authentication token has expired. Please log in again.

**Affected Functions:**
- `verify_token`
- `decode_jwt`

**Common Causes:**
- Session timeout reached
- Token TTL exceeded
- Server time synchronization issues

**Resolution Steps:**
1. Log in again to obtain a new token
2. Enable auto-refresh if available

---

### AUTH_004 - SSO Authentication Failed

**HTTP Status:** `401`  
**Severity:** `error`  
**Category:** `authentication`  
**Documentation:** [/docs/authentication#sso](/docs/authentication#sso)  

**Description:**  
Keycloak or other SSO provider authentication failed

**User Message:**  
> Single Sign-On authentication failed. Please try again or contact support.

**Affected Functions:**
- `sso_callback`
- `verify_sso_token`

**Common Causes:**
- SSO provider is unavailable
- Invalid SSO configuration
- User not authorized in SSO provider

**Resolution Steps:**
1. Retry authentication
2. Check SSO provider status
3. Contact administrator to verify SSO configuration

---

### GITLAB_003 - GitLab Token Mismatch

**HTTP Status:** `401`  
**Severity:** `warning`  
**Category:** `authentication`  
**Documentation:** [/docs/integrations/gitlab#tokens](/docs/integrations/gitlab#tokens)  

**Description:**  
GitLab /user endpoint returned different username than Account.provider_account_id

**User Message:**  
> The GitLab access token does not match your registered account.

**Affected Functions:**
- `validate_user_course`
- `register_user_course_account`

**Common Causes:**
- Using wrong personal access token
- Token belongs to different GitLab user
- Multiple GitLab accounts

**Resolution Steps:**
1. Use token from your registered GitLab account
2. Verify token username matches registered username
3. Re-register with correct account if needed

---

### GITLAB_005 - GitLab Token Required

**HTTP Status:** `401`  
**Severity:** `warning`  
**Category:** `authentication`  
**Documentation:** [/docs/integrations/gitlab#tokens](/docs/integrations/gitlab#tokens)  

**Description:**  
GitLab access token missing from request when required

**User Message:**  
> A GitLab personal access token is required for this operation.

**Affected Functions:**
- `validate_user_course`
- `register_user_course_account`

**Common Causes:**
- Token field empty or null
- Request missing provider_access_token field

**Resolution Steps:**
1. Generate GitLab personal access token with api scope
2. Include token in request payload
3. Verify token is not expired

---

## Authorization

### AUTHZ_001 - Insufficient Permissions

**HTTP Status:** `403`  
**Severity:** `warning`  
**Category:** `authorization`  
**Documentation:** [/docs/permissions](/docs/permissions)  

**Description:**  
User lacks required permissions for the requested operation

**User Message:**  
> You do not have permission to perform this action.

**Affected Functions:**
- `check_course_permissions`
- `check_admin`

**Common Causes:**
- User role insufficient for operation
- Course membership missing or insufficient
- Admin privileges required but not granted

**Resolution Steps:**
1. Contact course administrator to request appropriate permissions
2. Verify you are enrolled in the course with correct role
3. Check if admin privileges are required

---

### AUTHZ_002 - Admin Access Required

**HTTP Status:** `403`  
**Severity:** `warning`  
**Category:** `authorization`  
**Documentation:** [/docs/permissions#admin](/docs/permissions#admin)  

**Description:**  
Operation requires admin role but user is not an admin

**User Message:**  
> This operation requires administrator privileges.

**Affected Functions:**
- `check_admin`
- `require_admin`

**Common Causes:**
- User is not an administrator
- Admin role not assigned

**Resolution Steps:**
1. Contact system administrator
2. Request admin privileges if appropriate

---

### AUTHZ_003 - Course Access Denied

**HTTP Status:** `403`  
**Severity:** `warning`  
**Category:** `authorization`  
**Documentation:** [/docs/courses#enrollment](/docs/courses#enrollment)  

**Description:**  
User attempted to access course resources without proper enrollment

**User Message:**  
> You do not have access to this course.

**Affected Functions:**
- `check_course_permissions`
- `get_permitted_course_ids`

**Common Causes:**
- Not enrolled in course
- Enrollment pending approval
- Course archived or disabled

**Resolution Steps:**
1. Enroll in the course
2. Contact course instructor
3. Verify course is active

---

### AUTHZ_004 - Insufficient Course Role

**HTTP Status:** `403`  
**Severity:** `warning`  
**Category:** `authorization`  
**Documentation:** [/docs/permissions#course-roles](/docs/permissions#course-roles)  

**Description:**  
User's course role is below required level for operation

**User Message:**  
> Your course role is insufficient for this operation.

**Affected Functions:**
- `check_course_permissions`

**Common Causes:**
- Student trying to perform lecturer action
- Tutor trying to perform maintainer action
- Role hierarchy not satisfied

**Resolution Steps:**
1. Contact course administrator to request role upgrade
2. Verify operation requirements

---

### AUTHZ_005 - Role Escalation Denied

**HTTP Status:** `403`  
**Severity:** `error`  
**Category:** `authorization`  
**Documentation:** [/docs/permissions#role-assignment](/docs/permissions#role-assignment)  

**Description:**  
User attempted to assign a course role higher than their own privilege level

**User Message:**  
> You cannot assign a role higher than your own.

**Affected Functions:**
- `import_course_member`
- `update_course_member`

**Common Causes:**
- Lecturer trying to assign maintainer or owner role
- Tutor trying to assign lecturer role
- Privilege escalation attempt

**Resolution Steps:**
1. Request a user with higher privileges to perform this action
2. Assign a role at or below your own privilege level

---

## Conflict

### CONFLICT_001 - Resource Already Exists

**HTTP Status:** `409`  
**Severity:** `warning`  
**Category:** `conflict`  
**Documentation:** [/docs/api/conflicts](/docs/api/conflicts)  

**Description:**  
Unique constraint violation - duplicate key

**User Message:**  
> A resource with this identifier already exists.

**Affected Functions:**
- `create_entity`
- `db.add()`

**Common Causes:**
- Duplicate email address
- Duplicate name or identifier
- Unique constraint violation

**Resolution Steps:**
1. Use a different identifier
2. Update existing resource instead
3. Check for duplicate entries

---

### CONFLICT_002 - Concurrent Modification

**HTTP Status:** `409`  
**Severity:** `warning`  
**Category:** `conflict`  
**Documentation:** [/docs/api/concurrency](/docs/api/concurrency)  

**Description:**  
Optimistic locking failure - resource modified since read

**User Message:**  
> The resource was modified by another user. Please refresh and try again.

**Affected Functions:**
- `update_entity`
- `db.commit()`

**Common Causes:**
- Resource updated by another user
- Stale data in request
- Race condition

**Resolution Steps:**
1. Refresh resource data
2. Retry operation
3. Merge changes if appropriate

---

### VERSION_001 - Example Version Already Exists

**HTTP Status:** `409`  
**Severity:** `warning`  
**Category:** `conflict`  
**Documentation:** [/docs/api/examples#version-management](/docs/api/examples#version-management)  

**Description:**  
User attempted to create an example version that already exists without setting update_existing flag

**User Message:**  
> This version already exists for this example.

**Affected Functions:**
- `create_example_version`
- `upload_example`

**Common Causes:**
- Version tag already used
- Attempting to recreate existing version
- Missing update_existing flag in meta.yaml

**Resolution Steps:**
1. Set 'update_existing: true' in meta.yaml to update the existing version
2. Use a different version tag (e.g., increment version number)
3. Check existing versions before creating new ones

---

### GITLAB_004 - GitLab Account Already Linked

**HTTP Status:** `409`  
**Severity:** `warning`  
**Category:** `conflict`  
**Documentation:** [/docs/integrations/gitlab#registration](/docs/integrations/gitlab#registration)  

**Description:**  
Account table constraint violation - provider_account_id already exists for different user

**User Message:**  
> This GitLab username is already linked to another user.

**Affected Functions:**
- `register_user_course_account`

**Common Causes:**
- GitLab username already registered by another student
- Duplicate registration attempt
- Shared GitLab account (not allowed)

**Resolution Steps:**
1. Use a different GitLab username
2. Contact administrator if this is an error
3. Ensure each student uses their own GitLab account

---

## Database

### DB_001 - Database Connection Failed

**HTTP Status:** `503`  
**Severity:** `critical`  
**Category:** `database`  
**Retry After:** 120 seconds  
**Documentation:** [/docs/database](/docs/database)  

**Description:**  
PostgreSQL connection failed or timed out

**User Message:**  
> Unable to connect to the database.

**Affected Functions:**
- `get_db`
- `database.connect`

**Common Causes:**
- Database server down
- Connection pool exhausted
- Network issues
- Invalid credentials

**Resolution Steps:**
1. Check database server status
2. Verify database credentials
3. Check connection pool settings

---

### DB_002 - Database Query Failed

**HTTP Status:** `500`  
**Severity:** `error`  
**Category:** `database`  
**Documentation:** [/docs/database](/docs/database)  

**Description:**  
SQL query execution failed

**User Message:**  
> A database query failed. Please try again.

**Affected Functions:**
- `db.query()`
- `db.execute()`

**Common Causes:**
- SQL syntax error
- Constraint violation
- Database timeout

**Resolution Steps:**
1. Retry operation
2. Check query parameters
3. Contact administrator

---

### DB_003 - Transaction Failed

**HTTP Status:** `500`  
**Severity:** `error`  
**Category:** `database`  
**Documentation:** [/docs/database#transactions](/docs/database#transactions)  

**Description:**  
Database commit failed, transaction rolled back

**User Message:**  
> Database transaction failed and was rolled back.

**Affected Functions:**
- `db.commit()`

**Common Causes:**
- Constraint violation
- Deadlock
- Connection lost during transaction

**Resolution Steps:**
1. Retry operation
2. Check for conflicting updates
3. Verify data integrity

---

## External Service

### GITLAB_006 - GitLab Token Invalid

**HTTP Status:** `502`  
**Severity:** `error`  
**Category:** `external_service`  
**Documentation:** [/docs/integrations/gitlab#tokens](/docs/integrations/gitlab#tokens)  

**Description:**  
GitLab API returned 401/403 when validating token via /user endpoint

**User Message:**  
> The GitLab access token is invalid or has been revoked.

**Affected Functions:**
- `_fetch_gitlab_user_profile`

**Common Causes:**
- Token expired
- Token revoked or deleted
- Token missing required scopes (api)
- Token belongs to deleted GitLab user

**Resolution Steps:**
1. Generate new GitLab personal access token
2. Ensure token has api scope
3. Re-register with new token

---

### GITLAB_007 - GitLab API Unreachable

**HTTP Status:** `503`  
**Severity:** `error`  
**Category:** `external_service`  
**Retry After:** 60 seconds  
**Documentation:** [/docs/integrations/gitlab](/docs/integrations/gitlab)  

**Description:**  
Network error or timeout when calling GitLab API

**User Message:**  
> Unable to connect to GitLab API. Please try again later.

**Affected Functions:**
- `_fetch_gitlab_user_profile`

**Common Causes:**
- GitLab server temporarily down
- Network connectivity issues
- DNS resolution failure
- Firewall blocking request

**Resolution Steps:**
1. Wait and retry in a few moments
2. Check GitLab service status
3. Contact administrator if persists

---

### EXT_001 - GitLab Service Unavailable

**HTTP Status:** `503`  
**Severity:** `error`  
**Category:** `external_service`  
**Retry After:** 300 seconds  
**Documentation:** [/docs/integrations/gitlab](/docs/integrations/gitlab)  

**Description:**  
GitLab API request failed or timed out

**User Message:**  
> GitLab service is temporarily unavailable.

**Affected Functions:**
- `gitlab_client.request`
- `create_gitlab_group`
- `create_gitlab_repository`

**Common Causes:**
- GitLab server down
- Network connectivity issues
- GitLab API rate limiting

**Resolution Steps:**
1. Wait and retry
2. Check GitLab status page
3. Verify network connectivity

---

### EXT_002 - GitLab Authentication Failed

**HTTP Status:** `502`  
**Severity:** `error`  
**Category:** `external_service`  
**Documentation:** [/docs/integrations/gitlab#authentication](/docs/integrations/gitlab#authentication)  

**Description:**  
GitLab API token invalid or expired

**User Message:**  
> Failed to authenticate with GitLab.

**Affected Functions:**
- `gitlab_client.authenticate`

**Common Causes:**
- Invalid GitLab token
- Token expired
- Insufficient token permissions

**Resolution Steps:**
1. Verify GitLab token is valid
2. Check token permissions
3. Generate new token if needed

---

### EXT_003 - MinIO Service Unavailable

**HTTP Status:** `503`  
**Severity:** `error`  
**Category:** `external_service`  
**Retry After:** 60 seconds  
**Documentation:** [/docs/storage](/docs/storage)  

**Description:**  
MinIO/S3 service connection failed

**User Message:**  
> Object storage service is temporarily unavailable.

**Affected Functions:**
- `storage_service.upload_file`
- `storage_service.download_file`

**Common Causes:**
- MinIO server down
- Network issues
- Storage quota exceeded

**Resolution Steps:**
1. Retry operation
2. Check MinIO service status
3. Verify storage quota

---

### EXT_004 - Temporal Service Unavailable

**HTTP Status:** `503`  
**Severity:** `error`  
**Category:** `external_service`  
**Retry After:** 120 seconds  
**Documentation:** [/docs/workflows](/docs/workflows)  

**Description:**  
Temporal server connection failed

**User Message:**  
> Workflow service is temporarily unavailable.

**Affected Functions:**
- `task_executor.submit_task`
- `temporal_client.connect`

**Common Causes:**
- Temporal server down
- Network connectivity issues
- Worker not running

**Resolution Steps:**
1. Check Temporal server status
2. Verify worker is running
3. Retry operation

---

### EXT_005 - Task Queue Unavailable

**HTTP Status:** `503`  
**Severity:** `error`  
**Category:** `external_service`  
**Retry After:** 120 seconds  
**Documentation:** [/docs/testing-services](/docs/testing-services)  

**Description:**  
Temporal task queue has no available workers or queue configuration is invalid

**User Message:**  
> No worker available for the specified task queue.

**Affected Functions:**
- `create_test_run`
- `submit_task`

**Common Causes:**
- Service configuration missing 'temporal.task_queue' setting
- Task queue name incorrectly configured (not nested under 'temporal')
- Worker not running for the specified queue
- Temporal service unavailable

**Resolution Steps:**
1. Verify service configuration includes 'temporal.task_queue' setting
2. Ensure configuration follows the correct structure: {"temporal": {"task_queue": "queue-name"}}
3. Check that a worker is running for the specified task queue
4. Contact administrator to verify testing service setup

---

## Internal

### TASK_002 - Task Submission Failed

**HTTP Status:** `500`  
**Severity:** `error`  
**Category:** `internal`  
**Documentation:** [/docs/workflows#troubleshooting](/docs/workflows#troubleshooting)  

**Description:**  
Temporal workflow submission failed

**User Message:**  
> Failed to submit the task for execution.

**Affected Functions:**
- `task_executor.submit_task`
- `create_test_run`

**Common Causes:**
- Temporal service unavailable
- Invalid workflow parameters
- Network error

**Resolution Steps:**
1. Retry operation
2. Check Temporal service status
3. Contact administrator

---

### INT_001 - Internal Server Error

**HTTP Status:** `500`  
**Severity:** `critical`  
**Category:** `internal`  
**Documentation:** [/docs/support](/docs/support)  

**Description:**  
Unhandled exception or unexpected error condition

**User Message:**  
> An unexpected error occurred. Please try again later.

**Affected Functions:**
- `generic_handler`

**Common Causes:**
- Unhandled exception
- Bug in code
- Resource exhaustion

**Resolution Steps:**
1. Retry operation
2. Contact support with error details
3. Check server logs

---

### INT_002 - Configuration Error

**HTTP Status:** `500`  
**Severity:** `critical`  
**Category:** `internal`  
**Documentation:** [/docs/configuration](/docs/configuration)  

**Description:**  
Invalid or missing configuration settings

**User Message:**  
> Server configuration error. Please contact administrator.

**Affected Functions:**
- `load_settings`
- `initialize_service`

**Common Causes:**
- Missing environment variables
- Invalid configuration values
- Service misconfiguration

**Resolution Steps:**
1. Contact administrator
2. Check server configuration
3. Verify environment variables

---

## Not Found

### NF_001 - Resource Not Found

**HTTP Status:** `404`  
**Severity:** `info`  
**Category:** `not_found`  
**Documentation:** [/docs/api/resources](/docs/api/resources)  

**Description:**  
Database query returned no results for the requested resource

**User Message:**  
> The requested resource was not found.

**Affected Functions:**
- `get_by_id`
- `query.first()`

**Common Causes:**
- Resource deleted
- Invalid ID provided
- Resource archived
- Typo in URL or ID

**Resolution Steps:**
1. Verify the resource ID is correct
2. Check if resource was deleted
3. Review URL for typos

---

### NF_002 - User Not Found

**HTTP Status:** `404`  
**Severity:** `info`  
**Category:** `not_found`  
**Documentation:** [/docs/api/users](/docs/api/users)  

**Description:**  
User lookup failed - no user with given ID or email

**User Message:**  
> The specified user was not found.

**Affected Functions:**
- `get_user_by_id`
- `get_user_by_email`

**Common Causes:**
- Invalid user ID
- User account deleted
- Email address not registered

**Resolution Steps:**
1. Verify user ID or email
2. Check if user account exists

---

### NF_003 - Course Not Found

**HTTP Status:** `404`  
**Severity:** `info`  
**Category:** `not_found`  
**Documentation:** [/docs/api/courses](/docs/api/courses)  

**Description:**  
Course lookup failed or user lacks permission to view

**User Message:**  
> The specified course was not found.

**Affected Functions:**
- `get_course_by_id`
- `check_course_permissions`

**Common Causes:**
- Invalid course ID
- Course archived or deleted
- Insufficient permissions to view course

**Resolution Steps:**
1. Verify course ID
2. Check course enrollment status
3. Contact administrator

---

### NF_004 - Endpoint Not Found

**HTTP Status:** `404`  
**Severity:** `info`  
**Category:** `not_found`  
**Documentation:** [/docs/api](/docs/api)  

**Description:**  
HTTP route not registered in FastAPI application

**User Message:**  
> The requested API endpoint does not exist.

**Affected Functions:**
- `fastapi_router`

**Common Causes:**
- Typo in URL path
- Endpoint deprecated or removed
- Wrong API version
- Wrong HTTP method

**Resolution Steps:**
1. Check API documentation for correct endpoint
2. Verify API version
3. Check HTTP method (GET, POST, etc.)

---

### CONTENT_001 - Course Content Not Found

**HTTP Status:** `404`  
**Severity:** `info`  
**Category:** `not_found`  
**Documentation:** [/docs/api/course-content](/docs/api/course-content)  

**Description:**  
Course content lookup failed or user lacks permission

**User Message:**  
> The requested course content was not found.

**Affected Functions:**
- `get_course_content`
- `update_course_content`

**Common Causes:**
- Invalid course content ID
- Content archived or deleted
- Insufficient permissions

**Resolution Steps:**
1. Verify course content ID
2. Check enrollment status
3. Contact course instructor

---

### CONTENT_002 - Content Type Not Configured

**HTTP Status:** `404`  
**Severity:** `warning`  
**Category:** `not_found`  
**Documentation:** [/docs/api/course-content#types](/docs/api/course-content#types)  

**Description:**  
CourseContentType missing or misconfigured

**User Message:**  
> The content type for this assignment is not configured.

**Affected Functions:**
- `get_course_content_type`
- `validate_content_type`

**Common Causes:**
- Content type deleted
- Invalid content type ID
- Database inconsistency

**Resolution Steps:**
1. Contact course administrator
2. Verify content type configuration

---

### CONTENT_004 - Example Not Found

**HTTP Status:** `404`  
**Severity:** `info`  
**Category:** `not_found`  
**Documentation:** [/docs/api/examples](/docs/api/examples)  

**Description:**  
Example lookup by ID or identifier failed

**User Message:**  
> The requested example was not found.

**Affected Functions:**
- `get_example`
- `get_example_by_identifier`

**Common Causes:**
- Invalid example ID or identifier
- Example deleted
- No matching example

**Resolution Steps:**
1. Verify example ID or identifier
2. Check if example was deleted

---

### CONTENT_005 - Example Version Not Found

**HTTP Status:** `404`  
**Severity:** `info`  
**Category:** `not_found`  
**Documentation:** [/docs/api/examples#versions](/docs/api/examples#versions)  

**Description:**  
Example version lookup failed - no version with given tag/ID

**User Message:**  
> The requested example version was not found.

**Affected Functions:**
- `get_example_version`
- `get_version_by_tag`

**Common Causes:**
- Invalid version tag
- No versions exist
- Version deleted

**Resolution Steps:**
1. Verify version tag
2. Check available versions
3. Use 'latest' for most recent version

---

### DEPLOY_001 - Assignment Not Released

**HTTP Status:** `404`  
**Severity:** `warning`  
**Category:** `not_found`  
**Documentation:** [/docs/assignments#deployment](/docs/assignments#deployment)  

**Description:**  
CourseContentDeployment not found or not yet deployed

**User Message:**  
> This assignment has not been released yet.

**Affected Functions:**
- `get_deployment`
- `check_deployment_status`

**Common Causes:**
- Assignment not yet deployed
- Deployment pending
- Deployment deleted

**Resolution Steps:**
1. Wait for instructor to release assignment
2. Contact instructor for release date

---

### DEPLOY_002 - Deployment Not Found

**HTTP Status:** `404`  
**Severity:** `info`  
**Category:** `not_found`  
**Documentation:** [/docs/api/deployments](/docs/api/deployments)  

**Description:**  
Deployment lookup by ID failed

**User Message:**  
> The requested deployment was not found.

**Affected Functions:**
- `get_deployment_by_id`

**Common Causes:**
- Invalid deployment ID
- Deployment deleted

**Resolution Steps:**
1. Verify deployment ID
2. Check deployment status

---

### SUBMIT_001 - Submission Artifact Not Found

**HTTP Status:** `404`  
**Severity:** `info`  
**Category:** `not_found`  
**Documentation:** [/docs/api/submissions](/docs/api/submissions)  

**Description:**  
SubmissionArtifact lookup failed

**User Message:**  
> The requested submission artifact was not found.

**Affected Functions:**
- `get_submission_artifact`
- `create_test_run`

**Common Causes:**
- Invalid artifact ID
- No submission made yet
- Artifact deleted

**Resolution Steps:**
1. Verify artifact ID
2. Check if submission was made
3. Submit assignment first

---

### SUBMIT_002 - Submission Group Not Found

**HTTP Status:** `404`  
**Severity:** `info`  
**Category:** `not_found`  
**Documentation:** [/docs/assignments#groups](/docs/assignments#groups)  

**Description:**  
SubmissionGroup lookup failed or permission denied

**User Message:**  
> The requested submission group was not found.

**Affected Functions:**
- `get_submission_group`
- `check_group_membership`

**Common Causes:**
- Invalid submission group ID
- Not a member of group
- Group deleted

**Resolution Steps:**
1. Verify submission group ID
2. Check group membership
3. Contact instructor

---

### TASK_001 - Task Not Found

**HTTP Status:** `404`  
**Severity:** `info`  
**Category:** `not_found`  
**Documentation:** [/docs/api/tasks](/docs/api/tasks)  

**Description:**  
Result (task execution) lookup failed

**User Message:**  
> The requested task execution was not found.

**Affected Functions:**
- `get_test_status`
- `get_task_result`

**Common Causes:**
- Invalid task/result ID
- Task deleted
- Permission denied

**Resolution Steps:**
1. Verify task ID
2. Check task history
3. Verify permissions

---

### TASK_004 - Course Membership Not Found

**HTTP Status:** `404`  
**Severity:** `info`  
**Category:** `not_found`  
**Documentation:** [/docs/courses#enrollment](/docs/courses#enrollment)  

**Description:**  
CourseMember lookup failed for user and course

**User Message:**  
> You are not a member of this course.

**Affected Functions:**
- `get_course_member`
- `check_course_membership`

**Common Causes:**
- Not enrolled in course
- Enrollment pending
- Enrollment removed

**Resolution Steps:**
1. Enroll in the course
2. Contact instructor
3. Check enrollment status

---

## Not Implemented

### NIMPL_001 - Feature Not Implemented

**HTTP Status:** `501`  
**Severity:** `info`  
**Category:** `not_implemented`  
**Documentation:** [/docs/roadmap](/docs/roadmap)  

**Description:**  
Requested feature exists in API but not implemented

**User Message:**  
> This feature is not yet implemented.

**Affected Functions:**
- `not_implemented_handler`

**Common Causes:**
- Feature under development
- Deprecated endpoint
- Future functionality

**Resolution Steps:**
1. Check roadmap for implementation timeline
2. Use alternative endpoints
3. Contact support for updates

---

## Rate Limit

### RATE_001 - Rate Limit Exceeded

**HTTP Status:** `429`  
**Severity:** `warning`  
**Category:** `rate_limit`  
**Retry After:** 60 seconds  
**Documentation:** [/docs/api/rate-limits](/docs/api/rate-limits)  

**Description:**  
Request rate exceeded configured limits

**User Message:**  
> You have exceeded the rate limit. Please try again later.

**Affected Functions:**
- `rate_limit_middleware`
- `check_rate_limit`

**Common Causes:**
- Too many requests in short time
- API abuse
- Missing request throttling

**Resolution Steps:**
1. Wait for retry_after period
2. Implement request throttling
3. Use batch endpoints if available

---

### RATE_002 - Login Rate Limit Exceeded

**HTTP Status:** `429`  
**Severity:** `warning`  
**Category:** `rate_limit`  
**Retry After:** 60 seconds  
**Documentation:** [/docs/authentication#rate-limits](/docs/authentication#rate-limits)  

**Description:**  
Username-specific login rate limiting triggered

**User Message:**  
> Too many login attempts. Please try again later.

**Affected Functions:**
- `login_endpoint`
- `authenticate_user`

**Common Causes:**
- Multiple failed login attempts
- Automated login attempts
- Brute force attack

**Resolution Steps:**
1. Wait for the retry period (60 seconds)
2. Verify correct credentials
3. Contact administrator if locked out

---

### RATE_003 - Test Request Rate Limit Exceeded

**HTTP Status:** `429`  
**Severity:** `warning`  
**Category:** `rate_limit`  
**Retry After:** 1 seconds  
**Documentation:** [/docs/testing#rate-limits](/docs/testing#rate-limits)  

**Description:**  
User-specific test submission rate limiting triggered to prevent abuse

**User Message:**  
> Too many test requests. Please wait before submitting another test.

**Affected Functions:**
- `create_test_run`
- `check_user_rate_limit`

**Common Causes:**
- Submitting tests too rapidly
- Automated test submissions
- Multiple concurrent test requests

**Resolution Steps:**
1. Wait 1 second between test requests
2. Avoid rapid successive test submissions
3. Ensure only one test is submitted at a time

---

## Validation

### VAL_001 - Invalid Request Data

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/api/validation](/docs/api/validation)  

**Description:**  
Request body failed Pydantic validation

**User Message:**  
> The request data is invalid or malformed.

**Affected Functions:**
- `parse_request_body`
- `validate_dto`

**Common Causes:**
- Missing required fields
- Invalid data types
- Format constraints violated

**Resolution Steps:**
1. Check API documentation for required fields
2. Verify data types match schema
3. Review validation error details

---

### VAL_002 - Missing Required Field

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/api/validation](/docs/api/validation)  

**Description:**  
Required field not provided in request

**User Message:**  
> A required field is missing from the request.

**Affected Functions:**
- `validate_dto`

**Common Causes:**
- Field omitted from request body
- Null value provided for required field

**Resolution Steps:**
1. Include the required field in request
2. Check API documentation for required fields

---

### VAL_003 - Invalid Field Format

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/api/validation](/docs/api/validation)  

**Description:**  
Field value does not match expected format or pattern

**User Message:**  
> A field has an invalid format.

**Affected Functions:**
- `validate_email`
- `validate_uuid`
- `validate_url`

**Common Causes:**
- Invalid email format
- Malformed UUID
- URL format incorrect

**Resolution Steps:**
1. Check field format requirements
2. Use valid format for the field type

---

### VAL_004 - Invalid File Upload

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/api/file-uploads](/docs/api/file-uploads)  

**Description:**  
File upload validation failed

**User Message:**  
> The uploaded file is invalid or exceeds size limits.

**Affected Functions:**
- `validate_file_upload`
- `upload_file`

**Common Causes:**
- File too large
- Invalid file type
- Corrupted file

**Resolution Steps:**
1. Reduce file size
2. Use supported file types
3. Verify file is not corrupted

---

### CONTENT_003 - Invalid Content Type Operation

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/api/course-content#operations](/docs/api/course-content#operations)  

**Description:**  
Operation not supported for content type (e.g., examples on non-submittable)

**User Message:**  
> This operation is not valid for this content type.

**Affected Functions:**
- `assign_examples`
- `validate_content_operation`

**Common Causes:**
- Assigning examples to non-submittable content
- Invalid operation for content kind

**Resolution Steps:**
1. Check content type properties
2. Use correct operation for content type
3. Consult API documentation

---

### DEPLOY_003 - Repository Not Configured

**HTTP Status:** `400`  
**Severity:** `error`  
**Category:** `validation`  
**Documentation:** [/docs/integrations/gitlab#configuration](/docs/integrations/gitlab#configuration)  

**Description:**  
GitLab repository configuration missing from properties

**User Message:**  
> The GitLab repository is not configured for this resource.

**Affected Functions:**
- `validate_gitlab_config`
- `get_repository_config`

**Common Causes:**
- Organization GitLab not configured
- Course repository not created
- Student repository not initialized

**Resolution Steps:**
1. Contact administrator to configure GitLab
2. Verify organization settings
3. Wait for repository creation workflow

---

### DEPLOY_004 - Missing Deployment Information

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/assignments#deployment](/docs/assignments#deployment)  

**Description:**  
Deployment missing required fields (deployment_path, version_identifier)

**User Message:**  
> Required deployment information is missing.

**Affected Functions:**
- `validate_deployment`
- `create_test_run`

**Common Causes:**
- Incomplete deployment configuration
- Missing version identifier
- Missing deployment path

**Resolution Steps:**
1. Contact instructor
2. Wait for proper deployment

---

### SUBMIT_003 - Test Already Running

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/testing#status](/docs/testing#status)  

**Description:**  
Duplicate test attempt while existing test still running

**User Message:**  
> A test is already running for this submission.

**Affected Functions:**
- `create_test_run`
- `check_existing_test`

**Common Causes:**
- Multiple test requests
- Test already in progress

**Resolution Steps:**
1. Wait for current test to complete
2. Check test status

---

### SUBMIT_004 - Maximum Test Runs Exceeded

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/testing#limits](/docs/testing#limits)  

**Description:**  
Submission group max_test_runs limit reached

**User Message:**  
> You have reached the maximum number of test runs for this submission.

**Affected Functions:**
- `create_test_run`
- `check_test_limit`

**Common Causes:**
- Test limit configured on assignment
- Too many test attempts

**Resolution Steps:**
1. Review previous test results
2. Contact instructor for additional test runs

---

### SUBMIT_005 - Execution Backend Not Configured

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/testing#backends](/docs/testing#backends)  

**Description:**  
CourseContent missing execution_backend_id or ExecutionBackend not found

**User Message:**  
> The execution backend for this assignment is not configured.

**Affected Functions:**
- `create_test_run`
- `validate_execution_backend`

**Common Causes:**
- Execution backend not assigned
- Backend deleted or misconfigured

**Resolution Steps:**
1. Contact instructor
2. Verify assignment configuration

---

### SUBMIT_006 - Version Identifier Required

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/testing#versioning](/docs/testing#versioning)  

**Description:**  
No version_identifier found in artifact or request

**User Message:**  
> A version identifier (commit) is required for testing.

**Affected Functions:**
- `create_test_run`
- `validate_version`

**Common Causes:**
- Missing commit information
- Artifact missing version_identifier

**Resolution Steps:**
1. Submit with proper version information
2. Contact administrator

---

### SUBMIT_007 - Test Identifier Required

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/api/testing](/docs/api/testing)  

**Description:**  
Neither artifact_id nor submission_group_id provided in request

**User Message:**  
> You must provide either an artifact ID or submission group ID to test.

**Affected Functions:**
- `create_test_run`

**Common Causes:**
- Missing required parameters
- Invalid test request

**Resolution Steps:**
1. Provide artifact_id or submission_group_id
2. Check API documentation

---

### SUBMIT_008 - Artifact Already Tested

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/testing#duplicate-tests](/docs/testing#duplicate-tests)  

**Description:**  
User attempted to test an artifact that already has a successful test result

**User Message:**  
> You have already tested this artifact. Multiple tests are not allowed unless the previous test crashed or was cancelled.

**Affected Functions:**
- `create_test_run`
- `check_existing_test`

**Common Causes:**
- Duplicate test attempt
- Previous test completed successfully

**Resolution Steps:**
1. Review your previous test results
2. Submit a new version if you need to test again
3. Contact instructor if test needs to be reset

---

### TASK_003 - Unsupported Execution Backend

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/testing#backends](/docs/testing#backends)  

**Description:**  
ExecutionBackend.type not recognized or supported

**User Message:**  
> The execution backend type is not supported.

**Affected Functions:**
- `create_test_run`
- `validate_backend_type`

**Common Causes:**
- Invalid backend type configuration
- Backend not implemented

**Resolution Steps:**
1. Contact administrator
2. Verify backend configuration

---

### GITLAB_001 - GitLab Not Configured

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/integrations/gitlab](/docs/integrations/gitlab)  

**Description:**  
Course organization does not have GitLab provider configured

**User Message:**  
> GitLab integration is not configured for this course.

**Affected Functions:**
- `validate_user_course`
- `register_user_course_account`

**Common Causes:**
- Organization missing GitLab URL
- GitLab integration not enabled
- Course not configured for GitLab

**Resolution Steps:**
1. Contact course administrator
2. Verify course supports GitLab integration

---

### GITLAB_002 - GitLab Account Not Registered

**HTTP Status:** `400`  
**Severity:** `info`  
**Category:** `validation`  
**Documentation:** [/docs/integrations/gitlab#registration](/docs/integrations/gitlab#registration)  

**Description:**  
User has not linked GitLab account via Account table

**User Message:**  
> You have not registered your GitLab account for this course.

**Affected Functions:**
- `validate_user_course`

**Common Causes:**
- First time accessing course
- Account not yet linked

**Resolution Steps:**
1. Register your GitLab username and access token
2. Use POST /user/courses/{course_id}/register endpoint

---

### GITLAB_008 - Invalid GitLab Username

**HTTP Status:** `400`  
**Severity:** `warning`  
**Category:** `validation`  
**Documentation:** [/docs/integrations/gitlab#registration](/docs/integrations/gitlab#registration)  

**Description:**  
Provider account ID is empty or whitespace-only

**User Message:**  
> The GitLab username format is invalid.

**Affected Functions:**
- `register_user_course_account`

**Common Causes:**
- Empty username field
- Whitespace-only username
- Missing provider_account_id

**Resolution Steps:**
1. Provide your GitLab username
2. Verify username is not empty

---

