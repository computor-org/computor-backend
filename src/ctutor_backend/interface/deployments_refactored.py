"""
Refactored deployment configurations for Computor.

This module contains clean deployment configuration classes for creating
organization -> course family -> course hierarchies via Temporal workflows.

The deprecated CodeAbility classes have been moved to codeability_meta.py
and test-related enums should be in their own module.
"""

import yaml
from typing import Any, List, Optional, Dict
from pydantic import BaseModel, Field
from pydantic_yaml import to_yaml_str


class BaseDeployment(BaseModel):
    """Base class for all deployment configurations."""
    
    def get_deployment(self) -> str:
        """Get YAML representation of the deployment configuration."""
        return to_yaml_str(self, exclude_none=True, exclude_unset=True)

    def write_deployment(self, filename: str) -> None:
        """Write deployment configuration to a YAML file."""
        with open(filename, "w") as file:
            file.write(self.get_deployment())


class DeploymentFactory:
    """Factory for creating deployment configurations from YAML."""
    
    @staticmethod
    def read_deployment_from_string(classname, yamlstring: str):
        """Create deployment configuration from YAML string."""
        return classname(**yaml.safe_load(yamlstring))

    @staticmethod
    def read_deployment_from_file(classname, filename: str):
        """Create deployment configuration from YAML file."""
        with open(filename, "r") as file:
            if classname is not None:
                return classname(**yaml.safe_load(file))
            else:
                return yaml.safe_load(file)
    
    @staticmethod
    def read_deployment_from_file_raw(filename: str) -> dict:
        """Read raw YAML data from file."""
        with open(filename, "r") as file:
            return yaml.safe_load(file)


# User and Account Configuration Classes

class UserDeployment(BaseDeployment):
    """User deployment configuration for creating users in the system."""
    given_name: Optional[str] = Field(None, description="User's given name")
    family_name: Optional[str] = Field(None, description="User's family name")
    email: Optional[str] = Field(None, description="User's email address")
    number: Optional[str] = Field(None, description="User number/identifier (student ID)")
    username: Optional[str] = Field(None, description="Unique username")
    user_type: str = Field("user", description="Type of user account (user or token)")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional user properties")
    
    # Password for local authentication (optional)
    password: Optional[str] = Field(None, description="Initial password for the user")
    
    # GitLab-specific properties
    gitlab_username: Optional[str] = Field(None, description="GitLab username (if different from username)")
    gitlab_email: Optional[str] = Field(None, description="GitLab email (if different from email)")
    
    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        parts = []
        if self.given_name:
            parts.append(self.given_name)
        if self.family_name:
            parts.append(self.family_name)
        return ' '.join(parts) if parts else ''
    
    @property
    def display_name(self) -> str:
        """Get the user's display name."""
        full_name = self.full_name
        return full_name if full_name else (self.username or "Unknown User")


class AccountDeployment(BaseDeployment):
    """Account deployment configuration for external service accounts (e.g., GitLab)."""
    provider: str = Field(description="Account provider (e.g., 'gitlab', 'github')")
    type: str = Field(description="Account type (e.g., 'oauth', 'api_token')")
    provider_account_id: str = Field(description="Account ID in the provider system")
    
    # Additional provider-specific properties
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Provider-specific account properties")
    
    # GitLab-specific properties
    access_token: Optional[str] = Field(None, description="Access token for API access")
    refresh_token: Optional[str] = Field(None, description="Refresh token for token renewal")
    gitlab_username: Optional[str] = Field(None, description="GitLab username")
    gitlab_email: Optional[str] = Field(None, description="GitLab email")
    gitlab_user_id: Optional[int] = Field(None, description="GitLab user ID")
    is_admin: Optional[bool] = Field(False, description="Whether the GitLab user has admin privileges")
    can_create_group: Optional[bool] = Field(True, description="Whether the user can create GitLab groups")


class CourseMemberDeployment(BaseDeployment):
    """Course member deployment configuration for assigning users to courses."""
    # Course identification - either by ID or by path
    id: Optional[str] = Field(None, description="Direct course ID")
    # Alternative: specify by path
    organization: Optional[str] = Field(None, description="Organization path (e.g., 'kit')")
    course_family: Optional[str] = Field(None, description="Course family path (e.g., 'prog')")
    course: Optional[str] = Field(None, description="Course path (e.g., 'prog1')")
    
    # Course role - built-in roles: _student, _tutor, _lecturer, _maintainer, _owner
    role: str = Field("_student", description="Course role ID (e.g., '_student', '_tutor', '_lecturer')")
    
    # Course group - for students (by name or ID)
    group: Optional[str] = Field(None, description="Course group name or ID (required for students)")
    
    @property
    def is_path_based(self) -> bool:
        """Check if this deployment uses path-based identification."""
        return self.organization is not None and self.course_family is not None and self.course is not None
    
    @property
    def is_id_based(self) -> bool:
        """Check if this deployment uses ID-based identification."""
        return self.id is not None


class UserAccountDeployment(BaseDeployment):
    """Combined user and account deployment configuration."""
    user: UserDeployment = Field(description="User configuration")
    accounts: List[AccountDeployment] = Field(default_factory=list, description="Associated external accounts")
    course_members: List[CourseMemberDeployment] = Field(default_factory=list, description="Course memberships for this user")
    
    def get_primary_gitlab_account(self) -> Optional[AccountDeployment]:
        """Get the primary GitLab account if it exists."""
        for account in self.accounts:
            if account.type.lower() == "gitlab":
                return account
        return None


class UsersDeploymentConfig(BaseDeployment):
    """Configuration for deploying multiple users and their accounts."""
    users: List[UserAccountDeployment] = Field(description="List of users to deploy")
    
    def count_users(self) -> int:
        """Count the total number of users to be created."""
        return len(self.users)
    
    def count_accounts(self) -> int:
        """Count the total number of accounts to be created."""
        return sum(len(user.accounts) for user in self.users)
    
    def get_gitlab_users(self) -> List[UserAccountDeployment]:
        """Get users that have GitLab accounts."""
        return [user for user in self.users if user.get_primary_gitlab_account() is not None]


# Repository Configuration Classes

class GitLabConfig(BaseDeployment):
    """GitLab repository configuration."""
    url: Optional[str] = Field(None, description="GitLab instance URL")
    token: Optional[str] = Field(None, description="GitLab API token")
    parent: Optional[int] = Field(None, description="Parent group ID")
    full_path: Optional[str] = Field(None, description="Full path in GitLab")
    
    # Enhanced GitLab properties (populated after creation)
    group_id: Optional[int] = Field(None, description="GitLab group ID")
    parent_id: Optional[int] = Field(None, description="Parent group ID")
    namespace_id: Optional[int] = Field(None, description="Namespace ID")
    namespace_path: Optional[str] = Field(None, description="Namespace path")
    web_url: Optional[str] = Field(None, description="Web URL")
    visibility: Optional[str] = Field(None, description="Visibility level")
    last_synced_at: Optional[str] = Field(None, description="Last sync timestamp")


class GitHubConfig(BaseDeployment):
    """GitHub repository configuration (future support)."""
    url: Optional[str] = Field(None, description="GitHub instance URL")
    token: Optional[str] = Field(None, description="GitHub API token")
    organization: Optional[str] = Field(None, description="GitHub organization")


# Course Structure Configuration Classes

class ExecutionBackendConfig(BaseDeployment):
    """Full execution backend configuration for defining backends at root level."""
    slug: str = Field(description="Unique identifier for the backend")
    type: str = Field(description="Type of execution backend (e.g., temporal, prefect)")
    properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Backend-specific properties (e.g., task_queue, namespace, timeout settings)"
    )
    
class ExecutionBackendReference(BaseDeployment):
    """Reference to an execution backend by slug for linking to courses."""
    slug: str = Field(description="Slug of the execution backend to link")
    properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Course-specific overrides for this backend (optional)"
    )


class CourseContentTypeConfig(BaseDeployment):
    """Course content type configuration for deployment."""
    slug: str = Field(description="Unique identifier for the content type")
    title: Optional[str] = Field(None, description="Display title for the content type")
    description: Optional[str] = Field(None, description="Description of the content type")
    color: Optional[str] = Field("green", description="Display color (hex, rgb, hsl, or named color)")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional properties")
    kind: str = Field(description="ID of the course content kind (e.g., 'assignment', 'unit')")


class CourseProjects(BaseDeployment):
    """Configuration for course-related GitLab projects."""
    tests: Optional[str] = Field("tests", description="Path for tests project")
    student_template: Optional[str] = Field("student-template", description="Path for student template project")
    reference: Optional[str] = Field("reference", description="Path for reference solution project")
    examples: Optional[str] = Field("examples", description="Path for examples project")
    documents: Optional[str] = Field("documents", description="Path for documents project")


class OrganizationConfig(BaseDeployment):
    """Organization configuration."""
    name: str = Field(description="Organization display name")
    path: str = Field(description="Organization path/slug")
    description: Optional[str] = Field(None, description="Organization description")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Organization-specific settings")
    gitlab: Optional[GitLabConfig] = Field(None, description="GitLab configuration")
    github: Optional[GitHubConfig] = Field(None, description="GitHub configuration (future)")


class CourseFamilyConfig(BaseDeployment):
    """Course family configuration."""
    name: str = Field(description="Course family display name")
    path: str = Field(description="Course family path/slug")
    description: Optional[str] = Field(None, description="Course family description")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Course family-specific settings")


class CourseConfig(BaseDeployment):
    """Course configuration."""
    name: str = Field(description="Course display name")
    path: str = Field(description="Course path/slug")
    description: Optional[str] = Field(None, description="Course description")
    projects: Optional[CourseProjects] = Field(None, description="Course project structure")
    execution_backends: Optional[List[ExecutionBackendReference]] = Field(
        None,  # Changed from default_factory=list to None to make it truly optional
        description="References to execution backends to link to this course (by slug)"
    )
    content_types: Optional[List[CourseContentTypeConfig]] = Field(
        default_factory=list,
        description="Course content types to be created (assignments, units, etc.)"
    )
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Course-specific settings")


# Hierarchical configuration classes for nested structure

class HierarchicalCourseConfig(CourseConfig):
    """Course configuration for hierarchical deployment."""
    pass  # Inherits all fields from CourseConfig


class HierarchicalCourseFamilyConfig(CourseFamilyConfig):
    """Course family configuration with nested courses."""
    courses: List[HierarchicalCourseConfig] = Field(
        default_factory=list,
        description="List of courses in this course family"
    )


class HierarchicalOrganizationConfig(OrganizationConfig):
    """Organization configuration with nested course families."""
    course_families: List[HierarchicalCourseFamilyConfig] = Field(
        default_factory=list,
        description="List of course families in this organization"
    )


class ComputorDeploymentConfig(BaseDeployment):
    """
    Hierarchical deployment configuration for creating organization -> course family -> course structures.
    
    Supports deploying multiple organizations, each with multiple course families and courses.
    """
    # Execution backends to be created/ensured exist (root level definition)
    execution_backends: Optional[List[ExecutionBackendConfig]] = Field(
        None,  # Made optional to prevent validation errors when not provided
        description="List of execution backends to create or ensure exist in the system"
    )
    
    # Hierarchical structure - list of organizations with nested course families and courses
    organizations: List[HierarchicalOrganizationConfig] = Field(
        description="List of organizations with nested course families and courses"
    )
    
    # Users to be created and assigned to courses (optional)
    users: List[UserAccountDeployment] = Field(
        default_factory=list,
        description="List of users with their accounts and course memberships"
    )
    
    # Global deployment settings
    settings: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Global deployment settings"
    )
    
    def validate_structure(self) -> bool:
        """Validate the deployment configuration structure."""
        return len(self.organizations) > 0
    
    def count_entities(self) -> Dict[str, int]:
        """Count the total number of entities to be created."""
        org_count = len(self.organizations)
        family_count = sum(len(org.course_families) for org in self.organizations)
        course_count = sum(
            len(family.courses) 
            for org in self.organizations 
            for family in org.course_families
        )
        user_count = len(self.users)
        course_member_count = sum(len(user.course_members) for user in self.users)
        
        return {
            "organizations": org_count, 
            "course_families": family_count, 
            "courses": course_count,
            "users": user_count,
            "course_members": course_member_count
        }
    
    def get_deployment_paths(self) -> List[str]:
        """Get all the hierarchical paths that will be created."""
        paths = []
        for org in self.organizations:
            for family in org.course_families:
                for course in family.courses:
                    paths.append(f"{org.path}/{family.path}/{course.path}")
        return paths
    
    def get_full_course_path(self) -> str:
        """Get the full course path for the primary deployment."""
        if not self.organizations:
            return ""
        
        # Return the first organization/course family/course path
        org = self.organizations[0]
        if not org.course_families:
            return org.path
        
        family = org.course_families[0]
        if not family.courses:
            return f"{org.path}/{family.path}"
        
        course = family.courses[0]
        return f"{org.path}/{family.path}/{course.path}"


# Example deployment configurations

# Simple single organization deployment
EXAMPLE_DEPLOYMENT = ComputorDeploymentConfig(
    organizations=[
        HierarchicalOrganizationConfig(
            name="Computer Science Department",
            path="cs-dept",
            description="Department of Computer Science",
            gitlab=GitLabConfig(
                url="https://gitlab.example.com",
                token="<token>",
                parent=0
            ),
            course_families=[
                HierarchicalCourseFamilyConfig(
                    name="Programming Fundamentals",
                    path="programming",
                    description="Core programming courses",
                    courses=[
                        HierarchicalCourseConfig(
                            name="Python Programming",
                            path="python-2025s",
                            description="Introduction to Python programming",
                            projects=CourseProjects(
                                tests="tests",
                                student_template="student-template",
                                reference="reference",
                                examples="examples",
                                documents="docs"
                            ),
                            execution_backends=[
                                ExecutionBackendConfig(
                                    slug="python-3.11",
                                    type="python",
                                    version="3.11",
                                    settings={"timeout": 30}
                                )
                            ],
                            content_types=[
                                CourseContentTypeConfig(
                                    slug="homework",
                                    title="Homework Assignment",
                                    description="Weekly homework assignments",
                                    color="blue",
                                    kind="assignment"
                                ),
                                CourseContentTypeConfig(
                                    slug="exam",
                                    title="Exam",
                                    description="Course examinations",
                                    color="red",
                                    kind="assignment"
                                ),
                                CourseContentTypeConfig(
                                    slug="lecture",
                                    title="Lecture Material",
                                    description="Lecture notes and materials",
                                    color="green",
                                    kind="unit"
                                )
                            ]
                        )
                    ]
                )
            ]
        )
    ]
)

# Multi-organization deployment example
EXAMPLE_MULTI_DEPLOYMENT = ComputorDeploymentConfig(
    organizations=[
        HierarchicalOrganizationConfig(
            name="Technical University",
            path="tech-uni",
            description="Technical University Computer Science",
            gitlab=GitLabConfig(
                url="https://gitlab.example.com",
                token="<token>",
                parent=0
            ),
            course_families=[
                HierarchicalCourseFamilyConfig(
                    name="Programming Fundamentals",
                    path="programming",
                    description="Core programming courses",
                    courses=[
                        HierarchicalCourseConfig(
                            name="Python Programming",
                            path="python-2025s",
                            description="Introduction to Python programming",
                            execution_backends=[
                                ExecutionBackendConfig(
                                    slug="python-3.11",
                                    type="python",
                                    version="3.11",
                                    settings={"timeout": 30}
                                )
                            ]
                        ),
                        HierarchicalCourseConfig(
                            name="Java Programming",
                            path="java-2025s",
                            description="Introduction to Java programming",
                            execution_backends=[
                                ExecutionBackendConfig(
                                    slug="java-17",
                                    type="java",
                                    version="17",
                                    settings={"timeout": 45}
                                )
                            ]
                        )
                    ]
                ),
                HierarchicalCourseFamilyConfig(
                    name="Data Science",
                    path="data-science",
                    description="Data analysis and machine learning",
                    courses=[
                        HierarchicalCourseConfig(
                            name="Statistics with R",
                            path="stats-r-2025s",
                            description="Statistical analysis using R",
                            execution_backends=[
                                ExecutionBackendConfig(
                                    slug="r-4.3",
                                    type="r",
                                    version="4.3",
                                    settings={"timeout": 60}
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
        HierarchicalOrganizationConfig(
            name="Business School",
            path="business",
            description="Business School IT Department",
            course_families=[
                HierarchicalCourseFamilyConfig(
                    name="Business Analytics",
                    path="analytics",
                    description="Data analysis for business",
                    courses=[
                        HierarchicalCourseConfig(
                            name="Excel Analytics",
                            path="excel-2025s",
                            description="Advanced Excel for business analysis"
                        )
                    ]
                )
            ]
        )
    ],
    settings={
        "deployment_notes": "Multi-university deployment example",
        "created_by": "system_admin"
    }
)

# Example user deployment configurations

EXAMPLE_USERS_DEPLOYMENT = UsersDeploymentConfig(
    users=[
        UserAccountDeployment(
            user=UserDeployment(
                given_name="John",
                family_name="Doe",
                email="john.doe@university.edu",
                username="jdoe",
                number="12345678",
                password="Bv7#nM2$kL9@"
            ),
            accounts=[
                AccountDeployment(
                    provider="gitlab",
                    type="oauth",
                    provider_account_id="jdoe",
                    gitlab_username="jdoe",
                    gitlab_email="john.doe@university.edu",
                    can_create_group=False,
                    is_admin=False
                )
            ]
        ),
        UserAccountDeployment(
            user=UserDeployment(
                given_name="Jane",
                family_name="Smith",
                email="jane.smith@university.edu",
                username="jsmith",
                number="87654321",
                password="Wz4#pT6$mH8@"
            ),
            accounts=[
                AccountDeployment(
                    provider="gitlab",
                    type="oauth", 
                    provider_account_id="jsmith",
                    gitlab_username="jsmith",
                    gitlab_email="jane.smith@university.edu",
                    can_create_group=True,
                    is_admin=False
                )
            ]
        ),
        UserAccountDeployment(
            user=UserDeployment(
                given_name="Course",
                family_name="Manager",
                email="course.manager@university.edu",
                username="course_manager",
                user_type="user",
                password="Xk9#mZ8$qR7@"
            ),
            accounts=[
                AccountDeployment(
                    provider="gitlab",
                    type="oauth",
                    provider_account_id="course_manager",
                    gitlab_username="course_manager",
                    gitlab_email="course.manager@university.edu",
                    can_create_group=True,
                    is_admin=True
                )
            ]
        )
    ],
    default_password="DefaultPass123!",
    send_welcome_email=True,
    auto_activate=True,
    gitlab_create_users=True,
    gitlab_admin_token="<leave_empty_for_now>"
)