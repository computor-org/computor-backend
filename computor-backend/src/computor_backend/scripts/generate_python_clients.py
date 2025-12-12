#!/usr/bin/env python3
"""
Generate Python HTTP clients from OpenAPI specification.

This script generates typed endpoint clients for the computor-client package
by parsing the OpenAPI specification from the running API server.

Output structure:
    computor-client/src/computor_client/endpoints/
    ├── __init__.py          # Re-exports all clients
    ├── auth.py              # AuthClient (login, logout, refresh, etc.)
    ├── organizations.py     # OrganizationClient (CRUD + custom endpoints)
    ├── lecturers.py         # LecturerClient (role-specific endpoints)
    └── ...
"""

import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def fetch_openapi_spec(url: str = "http://localhost:8000/openapi.json") -> Dict[str, Any]:
    """Fetch OpenAPI spec from the running server."""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching OpenAPI spec from {url}: {e}")
        print("Make sure the API server is running.")
        return {}


def snake_to_pascal(name: str) -> str:
    """Convert snake_case or kebab-case to PascalCase."""
    name = name.replace("-", "_")
    return "".join(word.capitalize() for word in name.split("_"))


def extract_path_params(path: str) -> List[str]:
    """Extract path parameters from a route path."""
    return re.findall(r"\{(\w+)\}", path)


def sanitize_method_name(name: str) -> str:
    """Sanitize a string to be a valid Python identifier."""
    # Replace hyphens and other invalid chars with underscores
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Remove leading numbers
    name = re.sub(r'^[0-9]+', '', name)
    # Collapse multiple underscores
    name = re.sub(r'_+', '_', name)
    # Remove leading/trailing underscores
    name = name.strip('_')
    return name


def path_to_method_name(path: str, method: str, operation_id: str, base_segments: List[str]) -> str:
    """Generate a method name from path and operation."""
    segments = [s for s in path.split("/") if s and not s.startswith("{")]

    # Normalize base segments - also create the joined version for hyphenated paths
    normalized_base = [b.replace("-", "_").lower() for b in base_segments]
    joined_base = "_".join(normalized_base)  # e.g., "course_families"

    # Remove base segments from path
    remaining = []
    for seg in segments:
        seg_normalized = seg.replace("-", "_").lower()
        # Check if segment matches either individual base segments or the joined base
        if seg_normalized not in normalized_base and seg_normalized != joined_base:
            remaining.append(seg)

    if not remaining:
        # Standard CRUD
        if method == "GET" and not path.endswith("}"):
            return "list"
        elif method == "GET" and path.endswith("}"):
            return "get"
        elif method == "POST" and not any(s.startswith("{") for s in path.split("/")[-2:]):
            return "create"
        elif method == "PATCH" and path.count("{") == 1:
            return "update"
        elif method == "PUT" and path.count("{") == 1:
            return "replace"
        elif method == "DELETE" and path.count("{") == 1:
            return "delete"
        return method.lower()

    # Use remaining segments for method name
    name_parts = []
    for seg in remaining:
        seg_clean = sanitize_method_name(seg)
        if seg_clean:
            name_parts.append(seg_clean)

    method_name = "_".join(name_parts)

    # Add method prefix for non-standard operations
    if method == "POST" and "upload" not in method_name and "submit" not in method_name:
        if method_name not in ["login", "logout", "register", "refresh", "validate", "join", "sync"]:
            method_name = method_name
    elif method == "DELETE" and path.count("{") > 1:
        if not method_name.startswith("delete"):
            method_name = f"delete_{method_name}" if method_name else "delete"
    elif method == "GET" and path.count("{") > 1:
        if not method_name.startswith("get"):
            method_name = f"get_{method_name}" if method_name else "get"

    # Ensure final name is valid
    method_name = sanitize_method_name(method_name)
    return method_name if method_name else method.lower()


def find_schema_ref(schema: Dict[str, Any]) -> Optional[str]:
    """Extract schema reference name from a schema definition."""
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if "items" in schema and "$ref" in schema.get("items", {}):
        return schema["items"]["$ref"].split("/")[-1]
    if "anyOf" in schema:
        for item in schema["anyOf"]:
            if "$ref" in item:
                return item["$ref"].split("/")[-1]
    return None


def get_response_schema(operation: Dict[str, Any]) -> Tuple[Optional[str], bool]:
    """Get the response schema name and whether it's a list."""
    responses = operation.get("responses", {})
    for status in ["200", "201"]:
        if status in responses:
            content = responses[status].get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                is_list = schema.get("type") == "array"
                ref = find_schema_ref(schema)
                return ref, is_list
    return None, False


def get_request_schema(operation: Dict[str, Any]) -> Optional[str]:
    """Get the request body schema name for an operation."""
    body = operation.get("requestBody", {})
    content = body.get("content", {})
    if "application/json" in content:
        schema = content["application/json"].get("schema", {})
        return find_schema_ref(schema)
    return None


# Complete mapping of schema names to their module locations in computor_types
# Generated by scanning the actual source files
SCHEMA_TO_MODULE = {
    "AccountCreate": "accounts",
    "AccountDeployment": "deployments_refactored",
    "AccountGet": "accounts",
    "AccountInterface": "accounts",
    "AccountList": "accounts",
    "AccountQuery": "accounts",
    "AccountUpdate": "accounts",
    "AdminResetPasswordRequest": "password_management",
    "AdminSetPasswordRequest": "password_management",
    "ApiTokenAdminCreate": "api_tokens",
    "ApiTokenCreate": "api_tokens",
    "ApiTokenCreateResponse": "api_tokens",
    "ApiTokenGet": "api_tokens",
    "ApiTokenInterface": "api_tokens",
    "ApiTokenList": "api_tokens",
    "ApiTokenQuery": "api_tokens",
    "ApiTokenRevoke": "api_tokens",
    "ApiTokenUpdate": "api_tokens",
    "AssignExampleRequest": "deployment",
    "AssignExampleResponse": "lecturer_deployments",
    "AuthConfig": "auth",
    "AvailableTeam": "team_management",
    "BucketCreate": "storage",
    "BucketInfo": "storage",
    "BucketList": "storage",
    "BulkAssignExamplesRequest": "system",
    "ChangePasswordRequest": "password_management",
    "Claims": "permissions",
    "CommentCreate": "course_member_comments",
    "CommentUpdate": "course_member_comments",
    "ContentValidationCreate": "lecturer_content_validation",
    "ContentValidationGet": "lecturer_content_validation",
    "ContentValidationInterface": "lecturer_content_validation",
    "ContentValidationItem": "lecturer_content_validation",
    "ContentValidationResult": "lecturer_content_validation",
    "ContentTypeGradingStats": "course_member_gradings",
    "CourseContentConfig": "deployments_refactored",
    "CourseContentCreate": "course_contents",
    "CourseContentDeploymentCreate": "deployment",
    "CourseContentDeploymentGet": "deployment",
    "CourseContentDeploymentInterface": "deployment",
    "CourseContentDeploymentList": "deployment",
    "CourseContentDeploymentQuery": "deployment",
    "CourseContentDeploymentUpdate": "deployment",
    "CourseContentGet": "course_contents",
    "CourseContentInterface": "course_contents",
    "CourseContentKindCreate": "course_content_kind",
    "CourseContentKindGet": "course_content_kind",
    "CourseContentKindInterface": "course_content_kind",
    "CourseContentKindList": "course_content_kind",
    "CourseContentKindQuery": "course_content_kind",
    "CourseContentKindUpdate": "course_content_kind",
    "CourseContentLecturerGet": "lecturer_course_contents",
    "CourseContentLecturerInterface": "lecturer_course_contents",
    "CourseContentLecturerList": "lecturer_course_contents",
    "CourseContentLecturerQuery": "lecturer_course_contents",
    "CourseContentList": "course_contents",
    "CourseContentProperties": "course_contents",
    "CourseContentPropertiesGet": "course_contents",
    "CourseContentQuery": "course_contents",
    "CourseContentRepositoryLecturerGet": "lecturer_course_contents",
    "CourseContentStudentGet": "student_course_contents",
    "CourseContentStudentInterface": "student_course_contents",
    "CourseContentStudentList": "student_course_contents",
    "CourseContentStudentProperties": "student_course_contents",
    "CourseContentStudentQuery": "student_course_contents",
    "CourseContentStudentUpdate": "student_course_contents",
    "CourseContentTypeConfig": "deployments_refactored",
    "CourseContentTypeCreate": "course_content_types",
    "CourseContentTypeGet": "course_content_types",
    "CourseContentTypeInterface": "course_content_types",
    "CourseContentTypeList": "course_content_types",
    "CourseContentTypeQuery": "course_content_types",
    "CourseContentTypeUpdate": "course_content_types",
    "CourseContentUpdate": "course_contents",
    "CourseCreate": "courses",
    "CourseFamilyConfig": "deployments",
    "CourseFamilyCreate": "course_families",
    "CourseFamilyGet": "course_families",
    "CourseFamilyInterface": "course_families",
    "CourseFamilyList": "course_families",
    "CourseFamilyProperties": "course_families",
    "CourseFamilyPropertiesGet": "course_families",
    "CourseFamilyQuery": "course_families",
    "CourseFamilyTaskRequest": "system",
    "CourseFamilyUpdate": "course_families",
    "CourseGet": "courses",
    "CourseGroupConfig": "deployments",
    "CourseGroupCreate": "course_groups",
    "CourseGroupGet": "course_groups",
    "CourseGroupInterface": "course_groups",
    "CourseGroupList": "course_groups",
    "CourseGroupQuery": "course_groups",
    "CourseGroupUpdate": "course_groups",
    "CourseInterface": "courses",
    "CourseList": "courses",
    "CourseMemberCommentCreate": "course_member_comments",
    "CourseMemberCommentGet": "course_member_comments",
    "CourseMemberCommentInterface": "course_member_comments",
    "CourseMemberCommentList": "course_member_comments",
    "CourseMemberCommentQuery": "course_member_comments",
    "CourseMemberCommentUpdate": "course_member_comments",
    "CourseMemberCreate": "course_members",
    "CourseMemberDeployment": "deployments_refactored",
    "CourseMemberGet": "course_members",
    "CourseMemberGitLabConfig": "course_members",
    "CourseMemberGradingNode": "course_member_gradings",
    "CourseMemberGradingsGet": "course_member_gradings",
    "CourseMemberGradingsInterface": "course_member_gradings",
    "CourseMemberGradingsList": "course_member_gradings",
    "CourseMemberGradingsQuery": "course_member_gradings",
    "CourseMemberImportRequest": "course_member_import",
    "CourseMemberImportResponse": "course_member_import",
    "CourseMemberInterface": "course_members",
    "CourseMemberList": "course_members",
    "CourseMemberProperties": "course_members",
    "CourseMemberProviderAccountUpdate": "course_member_accounts",
    "CourseMemberQuery": "course_members",
    "CourseMemberReadinessStatus": "course_member_accounts",
    "CourseMemberUpdate": "course_members",
    "CourseMemberValidationRequest": "course_member_accounts",
    "CourseProjects": "deployments_refactored",
    "CourseProperties": "courses",
    "CoursePropertiesGet": "courses",
    "CourseQuery": "courses",
    "CourseReleaseUpdate": "system",
    "CourseRoleGet": "course_roles",
    "CourseRoleInterface": "course_roles",
    "CourseRoleList": "course_roles",
    "CourseRoleQuery": "course_roles",
    "CourseStudentGet": "student_courses",
    "CourseStudentInterface": "student_courses",
    "CourseStudentList": "student_courses",
    "CourseStudentQuery": "student_courses",
    "CourseStudentRepository": "student_courses",
    "CourseTaskRequest": "system",
    "CourseTutorGet": "tutor_courses",
    "CourseTutorInterface": "tutor_courses",
    "CourseTutorList": "tutor_courses",
    "CourseTutorQuery": "tutor_courses",
    "CourseTutorRepository": "tutor_courses",
    "CourseUpdate": "courses",
    "DeployExampleRequest": "deployment",
    "DeploymentGet": "lecturer_deployments",
    "DeploymentHistoryCreate": "deployment",
    "DeploymentHistoryGet": "deployment",
    "DeploymentHistoryInterface": "deployment",
    "DeploymentHistoryList": "deployment",
    "DeploymentList": "lecturer_deployments",
    "DeploymentMetadata": "deployment",
    "DeploymentSummary": "deployment",
    "DeploymentWithHistory": "deployment",
    "ErrorResponse": "errors",
    "ExampleBatchUploadRequest": "example",
    "ExampleCreate": "example",
    "ExampleDependencyCreate": "example",
    "ExampleDependencyGet": "example",
    "ExampleDownloadResponse": "example",
    "ExampleFileSet": "example",
    "ExampleGet": "example",
    "ExampleInterface": "example",
    "ExampleList": "example",
    "ExampleQuery": "example",
    "ExampleRepositoryCreate": "example",
    "ExampleRepositoryGet": "example",
    "ExampleRepositoryInterface": "example",
    "ExampleRepositoryList": "example",
    "ExampleRepositoryQuery": "example",
    "ExampleRepositoryUpdate": "example",
    "ExampleUpdate": "example",
    "ExampleUploadRequest": "example",
    "ExampleValidationResult": "lecturer_content_validation",
    "ExampleVersionCreate": "example",
    "ExampleVersionGet": "example",
    "ExampleVersionList": "example",
    "ExampleVersionQuery": "example",
    "ExtensionInterface": "extensions",
    "ExtensionMetadata": "extensions",
    "ExtensionPublishRequest": "extensions",
    "ExtensionPublishResponse": "extensions",
    "ExtensionVersionBase": "extensions",
    "ExtensionVersionDetail": "extensions",
    "ExtensionVersionListItem": "extensions",
    "ExtensionVersionListResponse": "extensions",
    "ExtensionVersionYankRequest": "extensions",
    "GenerateAssignmentsRequest": "system",
    "GenerateAssignmentsResponse": "system",
    "GenerateTemplateRequest": "system",
    "GenerateTemplateResponse": "system",
    "GitCommit": "git",
    "GitLabConfig": "deployments",
    "GitLabConfigGet": "deployments",
    "GitLabCredentials": "system",
    "GitLabPATCredentials": "password_management",
    "GitLabSyncRequest": "lecturer_gitlab_sync",
    "GitLabSyncResult": "lecturer_gitlab_sync",
    "GradedArtifactInfo": "tutor_grading",
    "GradedByCourseMember": "grading",
    "GradingAuthor": "grading",
    "GradingStatus": "grading",
    "GradingStudentView": "grading",
    "GradingSummary": "grading",
    "GroupClaimCreate": "group_claims",
    "GroupClaimGet": "group_claims",
    "GroupClaimInterface": "group_claims",
    "GroupClaimList": "group_claims",
    "GroupClaimQuery": "group_claims",
    "GroupClaimUpdate": "group_claims",
    "GroupCreate": "groups",
    "GroupGet": "groups",
    "GroupInterface": "groups",
    "GroupList": "groups",
    "GroupQuery": "groups",
    "GroupType": "groups",
    "GroupUpdate": "groups",
    "JoinTeamRequest": "team_management",
    "JoinTeamResponse": "team_management",
    "LanguageCreate": "languages",
    "LanguageGet": "languages",
    "LanguageInterface": "languages",
    "LanguageList": "languages",
    "LanguageQuery": "languages",
    "LanguageUpdate": "languages",
    "LeaveTeamResponse": "team_management",
    "ListQuery": "base",
    "LocalLoginRequest": "auth",
    "LocalLoginResponse": "auth",
    "LocalTokenRefreshRequest": "auth",
    "LocalTokenRefreshResponse": "auth",
    "LoginRequest": "auth",
    "LogoutRequest": "auth",
    "LogoutResponse": "auth",
    "MessageAuthor": "messages",
    "MessageCreate": "messages",
    "MessageGet": "messages",
    "MessageInterface": "messages",
    "MessageList": "messages",
    "MessageQuery": "messages",
    "MessageUpdate": "messages",
    "OrganizationConfig": "deployments",
    "OrganizationCreate": "organizations",
    "OrganizationGet": "organizations",
    "OrganizationInterface": "organizations",
    "OrganizationList": "organizations",
    "OrganizationProperties": "organizations",
    "OrganizationPropertiesGet": "organizations",
    "OrganizationQuery": "organizations",
    "OrganizationTaskRequest": "system",
    "OrganizationType": "organizations",
    "OrganizationUpdate": "organizations",
    "OrganizationUpdateTokenQuery": "organizations",
    "OrganizationUpdateTokenUpdate": "organizations",
    "PasswordOperationResponse": "password_management",
    "PasswordStatusResponse": "password_management",
    "PendingChange": "system",
    "PendingChangesResponse": "system",
    "PresignedUrlRequest": "storage",
    "PresignedUrlResponse": "storage",
    "Principal": "permissions",
    "ProfileCreate": "profiles",
    "ProfileGet": "profiles",
    "ProfileInterface": "profiles",
    "ProfileList": "profiles",
    "ProfileQuery": "profiles",
    "ProfileUpdate": "profiles",
    "ProviderAuthCredentials": "password_management",
    "ProviderInfo": "auth",
    "ReleaseCourseContentCreate": "system",
    "ReleaseCourseCreate": "system",
    "ReleaseOverride": "system",
    "ReleaseSelection": "system",
    "ReleaseStudentsCreate": "system",
    "ReleaseValidationError": "lecturer_deployments",
    "Repository": "repositories",
    "ResultArtifactCreate": "artifacts",
    "ResultArtifactInterface": "artifacts",
    "ResultArtifactListItem": "artifacts",
    "ResultArtifactQuery": "artifacts",
    "ResultCreate": "results",
    "ResultGet": "results",
    "ResultInterface": "results",
    "ResultList": "results",
    "ResultQuery": "results",
    "ResultStudentGet": "student_course_contents",
    "ResultStudentList": "student_course_contents",
    "ResultUpdate": "results",
    "ResultWithGrading": "results",
    "RoleClaimGet": "roles_claims",
    "RoleClaimInterface": "roles_claims",
    "RoleClaimList": "roles_claims",
    "RoleClaimQuery": "roles_claims",
    "RoleGet": "roles",
    "RoleInterface": "roles",
    "RoleList": "roles",
    "RoleQuery": "roles",
    "ServiceCreate": "services",
    "ServiceGet": "services",
    "ServiceInterface": "services",
    "ServiceList": "services",
    "ServiceQuery": "services",
    "ServiceTypeBase": "service_type",
    "ServiceTypeCreate": "service_type",
    "ServiceTypeGet": "service_type",
    "ServiceTypeInterface": "service_type",
    "ServiceTypeList": "service_type",
    "ServiceTypeQuery": "service_type",
    "ServiceTypeUpdate": "service_type",
    "ServiceUpdate": "services",
    "SessionCreate": "sessions",
    "SessionGet": "sessions",
    "SessionInterface": "sessions",
    "SessionList": "sessions",
    "SessionQuery": "sessions",
    "SessionUpdate": "sessions",
    "SetPasswordRequest": "password_management",
    "StatusQuery": "system",
    "StorageInterface": "storage",
    "StorageObjectCreate": "storage",
    "StorageObjectGet": "storage",
    "StorageObjectList": "storage",
    "StorageObjectMetadata": "storage",
    "StorageObjectQuery": "storage",
    "StorageObjectUpdate": "storage",
    "StorageUsageStats": "storage",
    "StudentCreate": "system",
    "StudentProfileCreate": "student_profile",
    "StudentProfileGet": "student_profile",
    "StudentProfileInterface": "student_profile",
    "StudentProfileList": "student_profile",
    "StudentProfileQuery": "student_profile",
    "StudentProfileUpdate": "student_profile",
    "SubmissionArtifactCreate": "artifacts",
    "SubmissionArtifactGet": "artifacts",
    "SubmissionArtifactInterface": "artifacts",
    "SubmissionArtifactList": "artifacts",
    "SubmissionArtifactQuery": "artifacts",
    "SubmissionArtifactUpdate": "artifacts",
    "SubmissionCreate": "submissions",
    "SubmissionGradeCreate": "artifacts",
    "SubmissionGradeDetail": "artifacts",
    "SubmissionGradeInterface": "artifacts",
    "SubmissionGradeListItem": "artifacts",
    "SubmissionGradeQuery": "artifacts",
    "SubmissionGradeUpdate": "artifacts",
    "SubmissionGroupCreate": "submission_groups",
    "SubmissionGroupDetailed": "submission_groups",
    "SubmissionGroupGet": "submission_groups",
    "SubmissionGroupGradingCreate": "grading",
    "SubmissionGroupGradingGet": "grading",
    "SubmissionGroupGradingInterface": "grading",
    "SubmissionGroupGradingList": "grading",
    "SubmissionGroupGradingQuery": "grading",
    "SubmissionGroupGradingUpdate": "grading",
    "SubmissionGroupInterface": "submission_groups",
    "SubmissionGroupList": "submission_groups",
    "SubmissionGroupMemberBasic": "student_course_contents",
    "SubmissionGroupMemberCreate": "submission_group_members",
    "SubmissionGroupMemberGet": "submission_group_members",
    "SubmissionGroupMemberInterface": "submission_group_members",
    "SubmissionGroupMemberList": "submission_group_members",
    "SubmissionGroupMemberProperties": "submission_group_members",
    "SubmissionGroupMemberQuery": "submission_group_members",
    "SubmissionGroupMemberUpdate": "submission_group_members",
    "SubmissionGroupProperties": "submission_groups",
    "SubmissionGroupQuery": "submission_groups",
    "SubmissionGroupRepository": "student_course_contents",
    "SubmissionGroupStudentGet": "student_course_contents",
    "SubmissionGroupStudentList": "student_course_contents",
    "SubmissionGroupStudentQuery": "submission_groups",
    "SubmissionGroupUpdate": "submission_groups",
    "SubmissionGroupWithGrading": "submission_groups",
    "SubmissionInterface": "submissions",
    "SubmissionListItem": "submissions",
    "SubmissionQuery": "submissions",
    "SubmissionReviewCreate": "artifacts",
    "SubmissionReviewDetail": "artifacts",
    "SubmissionReviewInterface": "artifacts",
    "SubmissionReviewListItem": "artifacts",
    "SubmissionReviewQuery": "artifacts",
    "SubmissionReviewUpdate": "artifacts",
    "SubmissionUploadResponseModel": "submissions",
    "SubmissionUploadedFile": "submissions",
    "TUGStudentExport": "system",
    "TaskInfo": "tasks",
    "TaskResponse": "system",
    "TaskResult": "tasks",
    "TaskStatus": "tasks",
    "TaskSubmission": "tasks",
    "TaskTrackerEntry": "tasks",
    "TeamCreate": "team_management",
    "TeamFormationRules": "team_management",
    "TeamLockRequest": "team_management",
    "TeamLockResponse": "team_management",
    "TeamMemberInfo": "team_management",
    "TeamResponse": "team_management",
    "TestCreate": "tests",
    "TestDependency": "codeability_meta",
    "TestJob": "tests",
    "TokenRefreshRequest": "auth",
    "TokenRefreshResponse": "auth",
    "TutorCourseMemberCourseContent": "tutor_course_members",
    "TutorCourseMemberGet": "tutor_course_members",
    "TutorCourseMemberList": "tutor_course_members",
    "TutorGradeCreate": "tutor_grading",
    "TutorGradeResponse": "tutor_grading",
    "TutorSubmissionGroupGet": "tutor_submission_groups",
    "TutorSubmissionGroupList": "tutor_submission_groups",
    "TutorSubmissionGroupMember": "tutor_submission_groups",
    "TutorSubmissionGroupQuery": "tutor_submission_groups",
    "UnassignExampleResponse": "lecturer_deployments",
    "UserCreate": "users",
    "UserGet": "users",
    "UserGroupCreate": "user_groups",
    "UserGroupGet": "user_groups",
    "UserGroupInterface": "user_groups",
    "UserGroupList": "user_groups",
    "UserGroupQuery": "user_groups",
    "UserGroupUpdate": "user_groups",
    "UserInterface": "users",
    "UserList": "users",
    "UserManagerResetPasswordRequest": "password_management",
    "UserPassword": "users",
    "UserQuery": "users",
    "UserRegistrationRequest": "auth",
    "UserRegistrationResponse": "auth",
    "UserRoleCreate": "user_roles",
    "UserRoleGet": "user_roles",
    "UserRoleInterface": "user_roles",
    "UserRoleList": "user_roles",
    "UserRoleQuery": "user_roles",
    "UserRoleUpdate": "user_roles",
    "UserUpdate": "users",
}

# Known enum types (these use constructor instead of model_validate)
ENUM_TYPES = {
    "TaskStatus",
    "GradingStatus",
    "OrganizationType",
    "GroupType",
}


def is_enum_type(schema_name: str) -> bool:
    """Check if a schema name is a known enum type."""
    return schema_name in ENUM_TYPES


def map_schema_to_import(schema_name: str) -> Optional[Tuple[str, str]]:
    """Map a schema name to its import path."""
    if not schema_name:
        return None

    # Skip internal FastAPI/Pydantic schemas
    if schema_name in ["HTTPValidationError", "ValidationError"] or schema_name.startswith("Body_"):
        return None

    # Skip schemas with namespaced names (e.g., computor_types__deployment__AssignExampleRequest)
    if "__" in schema_name:
        return None

    # Look up in the known mapping
    if schema_name in SCHEMA_TO_MODULE:
        module = SCHEMA_TO_MODULE[schema_name]
        return (f"computor_types.{module}", schema_name)

    return None


def group_operations_by_tag(spec: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Group all operations by their primary tag."""
    by_tag = defaultdict(list)

    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method not in ["get", "post", "put", "patch", "delete"]:
                continue

            tags = operation.get("tags", ["default"])
            primary_tag = tags[0] if tags else "default"
            primary_tag = primary_tag.replace("-", "_").replace(" ", "_").lower()

            by_tag[primary_tag].append({
                "path": path,
                "method": method.upper(),
                "operation": operation,
                "operation_id": operation.get("operationId", ""),
            })

    return dict(by_tag)


def generate_method(
    path: str,
    method: str,
    operation: Dict[str, Any],
    operation_id: str,
    tag: str,
) -> Tuple[str, Set[Tuple[str, str]]]:
    """Generate a single method for an endpoint."""
    imports = set()

    # Determine base segments from tag
    base_segments = tag.replace("_", "-").split("-")
    method_name = path_to_method_name(path, method, operation_id, base_segments)

    # Avoid duplicate method names
    path_params = extract_path_params(path)

    # Get schemas
    request_schema = get_request_schema(operation)
    response_schema, is_list_response = get_response_schema(operation)

    # Collect imports
    if request_schema:
        import_info = map_schema_to_import(request_schema)
        if import_info:
            imports.add(import_info)

    if response_schema:
        import_info = map_schema_to_import(response_schema)
        if import_info:
            imports.add(import_info)

    # Build parameters
    params = ["self"]
    for pp in path_params:
        params.append(f"{pp}: str")

    # Only add data parameter for methods that use request body (not GET/DELETE)
    if request_schema and map_schema_to_import(request_schema) and method in ["POST", "PUT", "PATCH"]:
        params.append(f"data: Union[{request_schema}, Dict[str, Any]]")

    # Query params (skip user_id as it's auto-injected)
    query_params = []
    for param in operation.get("parameters", []):
        if param.get("in") == "query" and param.get("name") != "user_id":
            pname = param["name"]
            required = param.get("required", False)
            if pname not in ["skip", "limit"]:
                query_params.append(pname)

    # Add query parameter for list endpoints to accept Query objects
    if method_name == "list":
        params.append("query: Optional[BaseModel] = None")

    # Return type
    if response_schema and map_schema_to_import(response_schema):
        if is_list_response:
            return_type = f"List[{response_schema}]"
        else:
            return_type = response_schema
    elif method == "DELETE" or operation.get("responses", {}).get("204"):
        return_type = "None"
    else:
        return_type = "Dict[str, Any]"

    # Build method
    docstring = operation.get("summary", f"{method} {path}")
    path_formatted = path
    for pp in path_params:
        path_formatted = path_formatted.replace(f"{{{pp}}}", "{" + pp + "}")

    lines = [
        f"    async def {method_name}(",
    ]
    for p in params:
        lines.append(f"        {p},")
    lines.extend([
        "        **kwargs: Any,",
        f"    ) -> {return_type}:",
        f'        """{docstring}"""',
    ])

    # HTTP call
    http_method = method.lower()
    if http_method == "get":
        if method_name == "list":
            lines.append(f'        params = query.model_dump(exclude_none=True) if query else {{}}'  )
            lines.append(f'        params.update(kwargs)')
            lines.append(f'        response = await self._http.get(')
            lines.append(f'            f"{path_formatted}",')
            lines.append(f'            params=params,')
            lines.append('        )')
        else:
            lines.append(f'        response = await self._http.get(f"{path_formatted}", params=kwargs)')
    elif http_method in ["post", "patch", "put"]:
        if request_schema and map_schema_to_import(request_schema):
            lines.append(f'        response = await self._http.{http_method}(f"{path_formatted}", json_data=data, params=kwargs)')
        else:
            lines.append(f'        response = await self._http.{http_method}(f"{path_formatted}", params=kwargs)')
    elif http_method == "delete":
        lines.append(f'        await self._http.delete(f"{path_formatted}", params=kwargs)')
        lines.append('        return')
        return "\n".join(lines), imports

    # Parse response
    if response_schema and map_schema_to_import(response_schema):
        if is_list_response:
            lines.append('        data = response.json()')
            lines.append('        if isinstance(data, list):')
            if is_enum_type(response_schema):
                lines.append(f'            return [{response_schema}(item) for item in data]')
            else:
                lines.append(f'            return [{response_schema}.model_validate(item) for item in data]')
            lines.append('        return []')
        else:
            if is_enum_type(response_schema):
                # Enums use constructor, not model_validate
                lines.append(f'        return {response_schema}(response.json())')
            else:
                lines.append(f'        return {response_schema}.model_validate(response.json())')
    else:
        if return_type == "None":
            lines.append('        return')
        else:
            lines.append('        return response.json()')

    return "\n".join(lines), imports


def generate_client_class(
    tag: str,
    operations: List[Dict[str, Any]],
) -> Tuple[str, Set[Tuple[str, str]], str]:
    """Generate a complete client class for a tag."""
    class_name = snake_to_pascal(tag) + "Client"

    all_imports = set()
    methods = []
    seen_method_names = set()

    for op in operations:
        method_code, imports = generate_method(
            op["path"],
            op["method"],
            op["operation"],
            op["operation_id"],
            tag,
        )

        # Extract method name to check for duplicates
        match = re.search(r"async def (\w+)\(", method_code)
        if match:
            method_name = match.group(1)
            if method_name in seen_method_names:
                # Add HTTP method and path hint to make unique
                http_method = op["method"].lower()
                path_hint = sanitize_method_name(op["path"].replace("/", "_").replace("{", "").replace("}", ""))
                # Use HTTP method as prefix to disambiguate
                new_name = f"{http_method}_{method_name}"
                if new_name in seen_method_names:
                    # Also add path hint
                    new_name = f"{http_method}_{path_hint[-30:]}" if len(path_hint) > 30 else f"{http_method}_{path_hint}"
                new_name = sanitize_method_name(new_name)
                method_code = method_code.replace(f"async def {method_name}(", f"async def {new_name}(")
                method_name = new_name
            seen_method_names.add(method_name)

        methods.append(method_code)
        all_imports.update(imports)

    lines = [
        f'class {class_name}:',
        f'    """',
        f'    Client for {tag.replace("_", " ")} endpoints.',
        f'    """',
        '',
        '    def __init__(self, http_client: AsyncHTTPClient) -> None:',
        '        self._http = http_client',
        '',
    ]

    for m in methods:
        lines.append(m)
        lines.append('')

    return "\n".join(lines), all_imports, class_name


def generate_file(tag: str, operations: List[Dict[str, Any]]) -> Tuple[str, str]:
    """Generate a complete Python file for a tag."""
    class_code, imports, class_name = generate_client_class(tag, operations)

    imports_by_module = defaultdict(set)
    for module, name in imports:
        imports_by_module[module].add(name)

    lines = [
        '"""',
        'Auto-generated endpoint client.',
        '',
        'This module is auto-generated from the OpenAPI specification.',
        'Run `bash generate.sh python-client` to regenerate.',
        '"""',
        '',
        'from typing import Any, Dict, List, Optional, Union',
        '',
        'from pydantic import BaseModel',
        '',
    ]

    for module in sorted(imports_by_module.keys()):
        names = sorted(imports_by_module[module])
        if len(names) == 1:
            lines.append(f'from {module} import {names[0]}')
        else:
            lines.append(f'from {module} import (')
            for name in names:
                lines.append(f'    {name},')
            lines.append(')')

    lines.extend([
        '',
        'from computor_client.http import AsyncHTTPClient',
        '',
        '',
        class_code,
    ])

    return "\n".join(lines), class_name


def main(output_dir: Optional[Path] = None, spec_url: str = "http://localhost:8000/openapi.json"):
    """Main generator entry point."""
    if output_dir is None:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent.parent.parent
        output_dir = project_root / "computor-client" / "src" / "computor_client" / "endpoints"

    print("Generating Python API clients from OpenAPI spec...")
    print(f"Output directory: {output_dir}")
    print()

    spec = fetch_openapi_spec(spec_url)
    if not spec:
        print("Failed to fetch OpenAPI spec.")
        return []

    output_dir.mkdir(parents=True, exist_ok=True)

    for file in output_dir.glob("*.py"):
        file.unlink()
    print("Cleaned output directory")
    print()

    operations_by_tag = group_operations_by_tag(spec)
    print(f"Found {len(operations_by_tag)} API tags")
    print()

    generated_files = []
    all_clients = []

    for tag in sorted(operations_by_tag.keys()):
        operations = operations_by_tag[tag]
        if tag in ["default"]:
            continue

        filename = tag + ".py"
        output_file = output_dir / filename

        try:
            file_content, class_name = generate_file(tag, operations)
            output_file.write_text(file_content + "\n")
            generated_files.append(output_file)
            all_clients.append((tag, class_name))
            print(f"Generated {filename} ({len(operations)} endpoints)")
        except Exception as e:
            print(f"Failed to generate {filename}: {e}")
            import traceback
            traceback.print_exc()

    print()

    # Generate __init__.py
    init_lines = [
        '"""',
        'Auto-generated endpoint clients.',
        '',
        'This module is auto-generated from the OpenAPI specification.',
        'Run `bash generate.sh python-client` to regenerate.',
        '"""',
        '',
    ]

    for tag, class_name in sorted(all_clients):
        init_lines.append(f'from computor_client.endpoints.{tag} import {class_name}')

    init_lines.extend(['', '__all__ = ['])
    for _, class_name in sorted(all_clients, key=lambda x: x[1]):
        init_lines.append(f'    "{class_name}",')
    init_lines.append(']')

    init_file = output_dir / "__init__.py"
    init_file.write_text("\n".join(init_lines) + "\n")
    print("Generated __init__.py")

    print()
    print("=" * 60)
    print(f"Generation Summary:")
    print(f"   Total tags: {len(operations_by_tag)}")
    print(f"   Generated files: {len(generated_files)}")
    print(f"   Total clients: {len(all_clients)}")
    print("=" * 60)

    return generated_files


if __name__ == "__main__":
    main()
