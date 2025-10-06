"""
Endpoint metadata for API routes.

This module provides endpoint paths for all resources without requiring
backend dependencies. Used by CLI and client packages.
"""

# Core entities
USERS_ENDPOINT = "users"
ORGANIZATIONS_ENDPOINT = "organizations"
COURSES_ENDPOINT = "courses"
COURSE_FAMILIES_ENDPOINT = "course-families"
COURSE_CONTENTS_ENDPOINT = "course-contents"
COURSE_CONTENT_TYPES_ENDPOINT = "course-content-types"
COURSE_GROUPS_ENDPOINT = "course-groups"
COURSE_MEMBERS_ENDPOINT = "course-members"
COURSE_ROLES_ENDPOINT = "course-roles"
RESULTS_ENDPOINT = "results"
ACCOUNTS_ENDPOINT = "accounts"
PROFILES_ENDPOINT = "profiles"
STUDENT_PROFILES_ENDPOINT = "student-profiles"
ROLES_ENDPOINT = "roles"
EXTENSIONS_ENDPOINT = "extensions"
EXAMPLES_ENDPOINT = "examples"

# Mapping from interface name to endpoint
ENDPOINT_MAP = {
    "UserInterface": USERS_ENDPOINT,
    "OrganizationInterface": ORGANIZATIONS_ENDPOINT,
    "CourseInterface": COURSES_ENDPOINT,
    "CourseFamilyInterface": COURSE_FAMILIES_ENDPOINT,
    "CourseContentInterface": COURSE_CONTENTS_ENDPOINT,
    "CourseContentTypeInterface": COURSE_CONTENT_TYPES_ENDPOINT,
    "CourseGroupInterface": COURSE_GROUPS_ENDPOINT,
    "CourseMemberInterface": COURSE_MEMBERS_ENDPOINT,
    "CourseRoleInterface": COURSE_ROLES_ENDPOINT,
    "ResultInterface": RESULTS_ENDPOINT,
    "AccountInterface": ACCOUNTS_ENDPOINT,
    "ProfileInterface": PROFILES_ENDPOINT,
    "StudentProfileInterface": STUDENT_PROFILES_ENDPOINT,
    "RoleInterface": ROLES_ENDPOINT,
    "ExtensionInterface": EXTENSIONS_ENDPOINT,
    "ExampleInterface": EXAMPLES_ENDPOINT,
}
