/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Common

 */



import type { ProviderAuthCredentials } from './auth';

import type { CourseContentTypeList, CourseExecutionBackendConfig, GradedByCourseMember, ResultStudentList, SubmissionGroupStudentList } from './courses';

import type { ExampleValidationResult, ExampleVersionList } from './examples';

import type { ErrorMessageFormat } from './messages';

import type { OrganizationGet } from './organizations';

import type { TaskStatus } from './tasks';



/**
 * Response with Coder session token.
 */
export interface CoderSessionResponse {
  success: boolean;
  session_token?: string | null;
  message: string;
}

export interface StudentProfileCreate {
  student_id?: string | null;
  student_email?: string | null;
  user_id?: string | null;
  organization_id: string;
}

export interface StudentProfileGet {
  student_id?: string | null;
  student_email?: string | null;
  user_id: string;
  organization_id: string;
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  organization?: OrganizationGet | null;
}

export interface StudentProfileList {
  id: string;
  student_id?: string | null;
  student_email?: string | null;
  user_id: string;
  organization_id: string;
}

export interface StudentProfileUpdate {
  student_id?: string | null;
  student_email?: string | null;
  properties?: any | null;
  organization_id?: string | null;
}

export interface StudentProfileQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  student_id?: string | null;
  student_email?: string | null;
  user_id?: string | null;
  organization_id?: string | null;
}

export interface GroupCreate {
  /** Group title */
  title: string;
  /** Group slug identifier */
  slug: string;
  /** Group description */
  description?: string | null;
  /** Type of group (fixed or dynamic) */
  type: GroupType;
  /** Additional group properties */
  properties?: any | null;
}

export interface GroupGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  /** Group unique identifier */
  id: string;
  /** Group title */
  title: string;
  /** Group description */
  description?: string | null;
  /** Group slug identifier */
  slug: string;
  /** Type of group */
  type: GroupType;
  /** Additional properties */
  properties?: any | null;
}

export interface GroupList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  /** Group unique identifier */
  id: string;
  /** Group title */
  title: string;
  /** Group description */
  description?: string | null;
  /** Group slug identifier */
  slug: string;
  /** Type of group */
  type: GroupType;
}

export interface GroupUpdate {
  /** Group title */
  title?: string | null;
  /** Group slug identifier */
  slug?: string | null;
  /** Group description */
  description?: string | null;
  /** Type of group */
  type?: GroupType | null;
  /** Additional properties */
  properties?: any | null;
}

export interface GroupQuery {
  skip?: number | null;
  limit?: number | null;
  /** Filter by group ID */
  id?: string | null;
  /** Filter by group title */
  title?: string | null;
  /** Filter by group slug */
  slug?: string | null;
  /** Filter by group type */
  type?: GroupType | null;
}

export interface FilterBase {
}

export interface EqualsFilter {
  eq: any;
}

export interface GreaterFilter {
  gt: any;
}

export interface LowerFilter {
  lt: any;
}

export interface NotEqualsFilter {
  ne: any;
}

export interface InFilter {
  in_: any[];
}

export interface NotInFilter {
  not_in: any[];
}

export interface LikeFilter {
  like: string;
}

export interface ILikeFilter {
  ilike: string;
}

export interface BetweenFilter {
  between: any[];
}

export interface IsNullFilter {
  is_null: boolean;
}

export interface NotNullFilter {
  not_null: boolean;
}

export interface StartswithFilter {
  startswith: string;
}

export interface EndswithFilter {
  endswith: string;
}

export interface ContainsFilter {
  contains: string;
}

export interface AndFilter {
  and_: EqualsFilter | GreaterFilter | LowerFilter | NotEqualsFilter | InFilter | NotInFilter | LikeFilter | ILikeFilter | BetweenFilter | IsNullFilter | NotNullFilter | StartswithFilter | EndswithFilter | ContainsFilter | AndFilter | OrFilter[];
}

export interface OrFilter {
  or_: EqualsFilter | GreaterFilter | LowerFilter | NotEqualsFilter | InFilter | NotInFilter | LikeFilter | ILikeFilter | BetweenFilter | IsNullFilter | NotNullFilter | StartswithFilter | EndswithFilter | ContainsFilter | AndFilter | OrFilter[];
}

/**
 * Base class for all deployment configurations.
 */
export interface BaseDeployment {
}

/**
 * User deployment configuration for creating users in the system.
 */
export interface UserDeployment {
  /** User's given name */
  given_name?: string | null;
  /** User's family name */
  family_name?: string | null;
  /** User's email address */
  email?: string | null;
  /** User number/identifier (student ID) */
  number?: string | null;
  /** Unique username */
  username?: string | null;
  /** Type of user account (user or token) */
  user_type?: string;
  /** Additional user properties */
  properties?: Record<string, any> | null;
  /** Initial password for the user */
  password?: string | null;
  /** System roles to assign to the user */
  roles?: string[] | null;
  /** GitLab username (if different from username) */
  gitlab_username?: string | null;
  /** GitLab email (if different from email) */
  gitlab_email?: string | null;
}

/**
 * Account deployment configuration for external service accounts (e.g., GitLab).
 */
export interface AccountDeployment {
  /** Account provider (e.g., 'gitlab', 'github') */
  provider: string;
  /** Account type (e.g., 'oauth', 'api_token') */
  type: string;
  /** Account ID in the provider system */
  provider_account_id: string;
  /** Provider-specific account properties */
  properties?: Record<string, any> | null;
  /** Access token for API access */
  access_token?: string | null;
  /** Refresh token for token renewal */
  refresh_token?: string | null;
  /** GitLab username */
  gitlab_username?: string | null;
  /** GitLab email */
  gitlab_email?: string | null;
  /** GitLab user ID */
  gitlab_user_id?: number | null;
  /** Whether the GitLab user has admin privileges */
  is_admin?: boolean | null;
  /** Whether the user can create GitLab groups */
  can_create_group?: boolean | null;
}

/**
 * Course member deployment configuration for assigning users to courses.
 */
export interface CourseMemberDeployment {
  /** Direct course ID */
  id?: string | null;
  /** Organization path (e.g., 'kit') */
  organization?: string | null;
  /** Course family path (e.g., 'prog') */
  course_family?: string | null;
  /** Course path (e.g., 'prog1') */
  course?: string | null;
  /** Course role ID (e.g., '_student', '_tutor', '_lecturer') */
  role?: string;
  /** Course group name or ID (required for students) */
  group?: string | null;
}

/**
 * Combined user and account deployment configuration.
 */
export interface UserAccountDeployment {
  /** User configuration */
  user: UserDeployment;
  /** Associated external accounts */
  accounts?: AccountDeployment[];
  /** Course memberships for this user */
  course_members?: CourseMemberDeployment[];
}

/**
 * Configuration for deploying multiple users and their accounts.
 */
export interface UsersDeploymentConfig {
  /** List of users to deploy */
  users: UserAccountDeployment[];
}

/**
 * GitLab repository configuration.
 */
export interface GitLabConfig {
  /** GitLab instance URL */
  url?: string | null;
  /** GitLab API token */
  token?: string | null;
  /** Parent group ID */
  parent?: number | null;
  /** Full path in GitLab */
  full_path?: string | null;
  /** GitLab group ID */
  group_id?: number | null;
  /** Parent group ID */
  parent_id?: number | null;
  /** Namespace ID */
  namespace_id?: number | null;
  /** Namespace path */
  namespace_path?: string | null;
  /** Web URL */
  web_url?: string | null;
  /** Visibility level */
  visibility?: string | null;
  /** Last sync timestamp */
  last_synced_at?: string | null;
}

/**
 * GitHub repository configuration (future support).
 */
export interface GitHubConfig {
  /** GitHub instance URL */
  url?: string | null;
  /** GitHub API token */
  token?: string | null;
  /** GitHub organization */
  organization?: string | null;
}

/**
 * Full execution backend configuration for defining backends at root level.
 */
export interface ExecutionBackendConfig {
  /** Unique identifier for the backend */
  slug: string;
  /** Type of execution backend (e.g., temporal, prefect) */
  type: string;
  /** Backend-specific properties (e.g., task_queue, namespace, timeout settings) */
  properties?: Record<string, any> | null;
}

/**
 * Reference to an execution backend by slug for linking to courses.
 */
export interface ExecutionBackendReference {
  /** Slug of the execution backend to link */
  slug: string;
  /** Course-specific overrides for this backend (optional) */
  properties?: Record<string, any> | null;
}

/**
 * User configuration for a service.
 * 
 * DEPRECATED: Use UserDeployment directly in ServiceConfig instead.
 * Kept for backwards compatibility.
 */
export interface ServiceUserConfig {
  /** Username for the service user */
  username: string;
  /** Email for the service user */
  email?: string | null;
  /** Given name */
  given_name?: string | null;
  /** Family name */
  family_name?: string | null;
}

/**
 * API token configuration for a service.
 */
export interface ServiceApiTokenConfig {
  /** Predefined API token (admin only). If not provided, a new token will be generated. */
  token?: string | null;
  /** Token name */
  name?: string | null;
  /** Initial scopes. Will be updated with course-specific scopes after deployment. */
  scopes?: string[] | null;
  /** Number of days until token expires. None means no expiration. */
  expires_days?: number | null;
  /** If True, delete existing token and recreate with predefined value. Requires 'token' to be set. */
  force_recreate?: boolean;
}

/**
 * Full service configuration for defining services at root level.
 * 
 * Services are deployed AFTER course hierarchy creation, allowing course_members
 * to be assigned to existing courses.
 */
export interface ServiceConfig {
  /** Unique identifier for the service */
  slug: string;
  /** ServiceType Ltree path (e.g., 'testing.temporal') */
  service_type_path: string;
  /** Programming language for testing services (e.g., 'python', 'matlab') */
  language?: string | null;
  /** User configuration for this service (same as regular users) */
  user: UserDeployment;
  /** API token configuration */
  api_token: ServiceApiTokenConfig;
  /** Service-specific configuration (task_queue, timeouts, etc.) */
  config?: Record<string, any> | null;
  /** Service description */
  description?: string | null;
  /** Course memberships for this service's user (e.g., _tutor role for testing services) */
  course_members?: CourseMemberDeployment[];
}

/**
 * Reference to a service by slug for linking to courses.
 */
export interface ServiceReference {
  /** Slug of the service to link */
  slug: string;
}

/**
 * Course content type configuration for deployment.
 */
export interface CourseContentTypeConfig {
  /** Unique identifier for the content type */
  slug: string;
  /** Display title for the content type */
  title?: string | null;
  /** Description of the content type */
  description?: string | null;
  /** Display color (hex, rgb, hsl, or named color) */
  color?: string | null;
  /** Additional properties */
  properties?: Record<string, any> | null;
  /** ID of the course content kind (e.g., 'assignment', 'unit') */
  kind: string;
}

/**
 * Configuration for course-related GitLab projects.
 */
export interface CourseProjects {
  /** Path for tests project */
  tests?: string | null;
  /** Path for student template project */
  student_template?: string | null;
  /** Path for reference solution project */
  reference?: string | null;
  /** Path for examples project */
  examples?: string | null;
  /** Path for documents project */
  documents?: string | null;
}

/**
 * Organization configuration.
 */
export interface OrganizationConfig {
  /** Organization display name */
  name: string;
  /** Organization path/slug */
  path: string;
  /** Organization description */
  description?: string | null;
  /** Organization-specific settings */
  settings?: Record<string, any> | null;
  /** GitLab configuration */
  gitlab?: GitLabConfig | null;
  /** GitHub configuration (future) */
  github?: GitHubConfig | null;
}

/**
 * Course family configuration.
 */
export interface CourseFamilyConfig {
  /** Course family display name */
  name: string;
  /** Course family path/slug */
  path: string;
  /** Course family description */
  description?: string | null;
  /** Course family-specific settings */
  settings?: Record<string, any> | null;
}

/**
 * Configuration for course content (assignments, units, etc.).
 */
export interface CourseContentConfig {
  /** Title of the course content (defaults from example if submittable) */
  title?: string | null;
  /** Hierarchical path using dots (optional; generated when omitted) */
  path?: string | null;
  /** Description of the content */
  description?: string | null;
  /** Slug of the course content type (must match a defined content_type) */
  content_type: string;
  /** Position for ordering (defaults to auto-increment) */
  position?: number | null;
  /** Maximum group size for submissions */
  max_group_size?: number | null;
  /** Maximum test runs allowed */
  max_test_runs?: number | null;
  /** Maximum submissions allowed */
  max_submissions?: number | null;
  /** Example identifier (e.g., 'week1.fibonacci') - required for submittable content */
  example_identifier?: string | null;
  /** Version tag of the example (e.g., 'v1.0', 'latest') - defaults to latest */
  example_version_tag?: string | null;
  /** Override execution backend slug for this content */
  execution_backend?: string | null;
  /** Nested course contents (for units containing assignments) */
  contents?: CourseContentConfig[] | null;
  /** Additional properties for the content */
  properties?: Record<string, any> | null;
}

/**
 * Course configuration.
 */
export interface CourseConfig {
  /** Course display name */
  name: string;
  /** Course path/slug */
  path: string;
  /** Course description */
  description?: string | null;
  /** Course project structure */
  projects?: CourseProjects | null;
  /** References to services to use for this course (by slug) */
  services?: ServiceReference[] | null;
  /** DEPRECATED: Use 'services' instead. References to execution backends to link to this course (by slug) */
  execution_backends?: ExecutionBackendReference[] | null;
  /** Course content types to be created (assignments, units, etc.) */
  content_types?: CourseContentTypeConfig[] | null;
  /** Course contents hierarchy (assignments, units, etc.) */
  contents?: CourseContentConfig[] | null;
  /** Course-specific settings */
  settings?: Record<string, any> | null;
}

/**
 * Course configuration for hierarchical deployment.
 */
export interface HierarchicalCourseConfig {
  /** Course display name */
  name: string;
  /** Course path/slug */
  path: string;
  /** Course description */
  description?: string | null;
  /** Course project structure */
  projects?: CourseProjects | null;
  /** References to services to use for this course (by slug) */
  services?: ServiceReference[] | null;
  /** DEPRECATED: Use 'services' instead. References to execution backends to link to this course (by slug) */
  execution_backends?: ExecutionBackendReference[] | null;
  /** Course content types to be created (assignments, units, etc.) */
  content_types?: CourseContentTypeConfig[] | null;
  /** Course contents hierarchy (assignments, units, etc.) */
  contents?: CourseContentConfig[] | null;
  /** Course-specific settings */
  settings?: Record<string, any> | null;
}

/**
 * Course family configuration with nested courses.
 */
export interface HierarchicalCourseFamilyConfig {
  /** Course family display name */
  name: string;
  /** Course family path/slug */
  path: string;
  /** Course family description */
  description?: string | null;
  /** Course family-specific settings */
  settings?: Record<string, any> | null;
  /** List of courses in this course family */
  courses?: HierarchicalCourseConfig[];
}

/**
 * Organization configuration with nested course families.
 */
export interface HierarchicalOrganizationConfig {
  /** Organization display name */
  name: string;
  /** Organization path/slug */
  path: string;
  /** Organization description */
  description?: string | null;
  /** Organization-specific settings */
  settings?: Record<string, any> | null;
  /** GitLab configuration */
  gitlab?: GitLabConfig | null;
  /** GitHub configuration (future) */
  github?: GitHubConfig | null;
  /** List of course families in this organization */
  course_families?: HierarchicalCourseFamilyConfig[];
}

/**
 * Hierarchical deployment configuration for creating organization -> course family -> course structures.
 * 
 * Supports deploying multiple organizations, each with multiple course families and courses.
 */
export interface ComputorDeploymentConfig {
  /** List of services to create or ensure exist in the system (deployed in Phase 1) */
  services?: ServiceConfig[] | null;
  /** DEPRECATED: Use 'services' instead. List of execution backends to create or ensure exist in the system */
  execution_backends?: ExecutionBackendConfig[] | null;
  /** List of organizations with nested course families and courses */
  organizations?: HierarchicalOrganizationConfig[];
  /** List of users with their accounts and course memberships */
  users?: UserAccountDeployment[];
  /** Global deployment settings */
  settings?: Record<string, any> | null;
  /** Optional list of VSIX packages to upload before deployment */
  extensions_upload?: ExtensionUploadConfig[] | null;
  /** If provided, uploads examples before hierarchy deployment */
  examples_upload?: ExamplesUploadConfig | null;
}

export interface ExtensionUploadConfig {
  /** Relative path to the .vsix package to upload */
  path: string;
  /** Override publisher (defaults to manifest) */
  publisher?: string | null;
  /** Override extension name (defaults to manifest) */
  name?: string | null;
  /** Override display name stored in metadata */
  display_name?: string | null;
  /** Override description stored in metadata */
  description?: string | null;
  /** Override VS Code engine compatibility range */
  engine_range?: string | null;
}

export interface ExamplesUploadConfig {
  /** Name of the Example Repository to use/create */
  repository: string;
  /** Relative path to directory containing example subdirectories */
  path: string;
}

export interface SubmissionGroupProperties {
  gitlab?: GitLabConfig | null;
}

export interface SubmissionGroupCreate {
  properties?: SubmissionGroupProperties | null;
  display_name?: string | null;
  max_group_size?: number;
  max_submissions?: number | null;
  course_content_id: string;
  status?: string | null;
}

export interface SubmissionGroupGet {
  properties?: SubmissionGroupProperties | null;
  display_name?: string | null;
  max_group_size?: number;
  max_submissions?: number | null;
  course_content_id: string;
  status?: string | null;
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  course_id: string;
  last_submitted_result_id?: string | null;
}

export interface SubmissionGroupList {
  id: string;
  properties?: SubmissionGroupProperties | null;
  display_name?: string | null;
  max_group_size: number;
  max_submissions?: number | null;
  course_id: string;
  course_content_id: string;
  status?: string | null;
  last_submitted_result_id?: string | null;
}

export interface SubmissionGroupUpdate {
  properties?: SubmissionGroupProperties | null;
  display_name?: string | null;
  max_group_size?: number | null;
  max_submissions?: number | null;
  status?: string | null;
}

export interface SubmissionGroupQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  display_name?: string | null;
  max_group_size?: number | null;
  max_submissions?: number | null;
  course_id?: string | null;
  course_content_id?: string | null;
  properties?: SubmissionGroupProperties | null;
  status?: string | null;
}

/**
 * Query parameters for student submission groups
 */
export interface SubmissionGroupStudentQuery {
  course_id?: string | null;
  course_content_id?: string | null;
  has_repository?: boolean | null;
  is_graded?: boolean | null;
}

/**
 * Submission group with latest grading information.
 */
export interface SubmissionGroupWithGrading {
  properties?: SubmissionGroupProperties | null;
  display_name?: string | null;
  max_group_size?: number;
  max_submissions?: number | null;
  course_content_id: string;
  status?: string | null;
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  course_id: string;
  last_submitted_result_id?: string | null;
  latest_grading?: any | null;
  grading_count?: number;
  last_submitted_at?: string | null;
}

/**
 * Detailed submission group information including members and gradings.
 */
export interface SubmissionGroupDetailed {
  id: string;
  course_id: string;
  course_content_id: string;
  properties?: SubmissionGroupProperties | null;
  display_name?: string | null;
  max_group_size: number;
  max_submissions?: number | null;
  max_test_runs?: number | null;
  members?: any[];
  gradings?: any[];
  last_submitted_result?: any | null;
  current_group_size?: number;
  submission_count?: number;
  test_run_count?: number;
  latest_grade?: number | null;
  latest_grading_status?: GradingStatus | null;
  created_at: string;
  updated_at: string;
}

export interface StudentTemplateSettings {
  mr_default_target_self?: boolean;
  merge_method?: MergeMethod;
  only_allow_merge_if_pipeline_succeeds?: boolean;
  only_allow_merge_if_all_discussions_are_resolved?: boolean;
}

/**
 * Represents a test dependency with slug and version constraint.
 */
export interface TestDependency {
  /** Hierarchical slug of the dependency example (e.g., 'physics.math.vectors') */
  slug: string;
  /** Version constraint (e.g., '>=1.2.0', '^2.1.0', '1.0.0'). If not specified, uses latest version. */
  version?: string | null;
}

/**
 * Base class for all CodeAbility meta models.
 */
export interface CodeAbilityBase {
}

/**
 * Link to external resources.
 */
export interface CodeAbilityLink {
  /** Description of the link */
  description: string;
  /** URL of the link */
  url: string;
}

/**
 * Person information for authors/maintainers.
 */
export interface CodeAbilityPerson {
  /** Full name */
  name?: string | null;
  /** Email address */
  email?: string | null;
  /** Institutional affiliation */
  affiliation?: string | null;
}

/**
 * Properties specific to assignment-level meta.
 */
export interface CodeAbilityMetaProperties {
  /** Files that students must submit */
  studentSubmissionFiles?: string[] | null;
  /** Additional files provided to students */
  additionalFiles?: string[] | null;
  /** Test files for automated grading */
  testFiles?: string[] | null;
  /** Template files for student projects */
  studentTemplates?: string[] | null;
  /** List of example dependencies. Can be simple strings (slugs) or objects with slug and version constraints */
  testDependencies?: string | TestDependency[] | null;
  /** Execution backend configuration for this assignment */
  executionBackend?: CourseExecutionBackendConfig | null;
}

/**
 * Meta information for assignments/examples.
 */
export interface CodeAbilityMeta {
  /** Version of the meta format */
  version?: string | null;
  /** Unique identifier for the assignment */
  slug?: string | null;
  /** Human-readable title */
  title?: string | null;
  /** Detailed description of the content */
  description?: string | null;
  /** Primary language of the content (e.g., 'en', 'de', 'fr', etc.) */
  language?: string | null;
  /** License information */
  license?: string | null;
  /** Content authors */
  authors?: CodeAbilityPerson[] | null;
  /** Content maintainers */
  maintainers?: CodeAbilityPerson[] | null;
  /** Related links */
  links?: CodeAbilityLink[] | null;
  /** Supporting material links */
  supportingMaterial?: CodeAbilityLink[] | null;
  /** Keywords for categorization */
  keywords?: string[] | null;
  /** Assignment-specific properties */
  properties?: CodeAbilityMetaProperties | null;
}

export interface Repository {
  url: string;
  user?: string | null;
  token?: string | null;
  branch?: string | null;
  path?: string | null;
  commit?: string | null;
}

export interface ListQuery {
  skip?: number | null;
  limit?: number | null;
}

export interface BaseEntityList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
}

export interface BaseEntityGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
}

/**
 * Base fields shared across all service type DTOs.
 */
export interface ServiceTypeBase {
  /** Hierarchical path (e.g., 'testing.python', 'review.llm.gpt4') */
  path: string;
  /** Display name */
  name: string;
  /** Detailed description */
  description?: string | null;
  /** Category: worker, testing, review, metrics, integration */
  category: string;
  /** Python module providing functionality */
  plugin_module?: string | null;
  /** JSON Schema for config validation */
  schema_?: any | null;
  /** Icon identifier */
  icon?: string | null;
  /** Hex color for UI (e.g., #FF5733) */
  color?: string | null;
  /** Whether this service type is enabled */
  enabled?: boolean;
  /** Additional properties */
  properties?: any | null;
}

/**
 * DTO for creating a new service type.
 */
export interface ServiceTypeCreate {
  /** Hierarchical path (e.g., 'testing.python', 'review.llm.gpt4') */
  path: string;
  /** Display name */
  name: string;
  /** Detailed description */
  description?: string | null;
  /** Category: worker, testing, review, metrics, integration */
  category: string;
  /** Python module providing functionality */
  plugin_module?: string | null;
  /** JSON Schema for config validation */
  schema_?: any | null;
  /** Icon identifier */
  icon?: string | null;
  /** Hex color for UI (e.g., #FF5733) */
  color?: string | null;
  /** Whether this service type is enabled */
  enabled?: boolean;
  /** Additional properties */
  properties?: any | null;
}

/**
 * DTO for updating an existing service type.
 */
export interface ServiceTypeUpdate {
  name?: string | null;
  description?: string | null;
  category?: string | null;
  plugin_module?: string | null;
  schema_?: any | null;
  icon?: string | null;
  color?: string | null;
  enabled?: boolean | null;
  properties?: any | null;
}

/**
 * DTO for listing service types (minimal fields).
 */
export interface ServiceTypeList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  /** UUID */
  id: string;
  /** Hierarchical path */
  path: string;
  /** Display name */
  name: string;
  /** Category */
  category: string;
  /** Enabled status */
  enabled: boolean;
  /** Icon identifier */
  icon?: string | null;
  /** Hex color */
  color?: string | null;
  /** Version number */
  version: number;
}

/**
 * DTO for getting a single service type (full fields).
 */
export interface ServiceTypeGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  /** UUID */
  id: string;
  /** Hierarchical path */
  path: string;
  /** Display name */
  name: string;
  /** Description */
  description?: string | null;
  /** Category */
  category: string;
  /** Python module */
  plugin_module?: string | null;
  /** JSON Schema */
  schema_?: any | null;
  /** Icon identifier */
  icon?: string | null;
  /** Hex color */
  color?: string | null;
  /** Enabled status */
  enabled: boolean;
  /** Additional properties */
  properties?: any;
  /** Version number */
  version: number;
}

/**
 * Query parameters for filtering service types.
 */
export interface ServiceTypeQuery {
  skip?: number | null;
  limit?: number | null;
  /** Filter by UUID */
  id?: string | null;
  /** Filter by exact path */
  path?: string | null;
  /** Filter by path descendants (e.g., 'testing' returns all testing.*) */
  path_descendant?: string | null;
  /** Filter by path pattern (ltree lquery) */
  path_pattern?: string | null;
  /** Filter by category */
  category?: string | null;
  /** Filter by enabled status */
  enabled?: boolean | null;
  /** Filter by plugin module */
  plugin_module?: string | null;
}

export interface GitlabGroupProjectConfig {
  name?: string | null;
  path: string;
}

export interface CourseProjectsConfig {
  tests: GitlabGroupProjectConfig;
  student_template: GitlabGroupProjectConfig;
  reference: GitlabGroupProjectConfig;
  images: GitlabGroupProjectConfig;
  documents: GitlabGroupProjectConfig;
}

export interface ApiConfig {
  user: string;
  password: string;
  url: string;
}

export interface RepositoryConfig {
  settings?: any | null;
}

export interface GitLabConfigGet {
  settings?: any | null;
  url?: string | null;
  full_path?: string | null;
  directory?: string | null;
  registry?: string | null;
  parent?: number | null;
  group_id?: number | null;
  parent_id?: number | null;
  namespace_id?: number | null;
  namespace_path?: string | null;
  web_url?: string | null;
  visibility?: string | null;
  last_synced_at?: string | null;
}

export interface TypeConfig {
  kind: string;
  slug: string;
  title: string;
  color?: string | null;
  description?: string | null;
  properties?: any;
}

export interface CourseGroupConfig {
  name: string;
}

export interface FileSourceConfig {
  url: string;
  token?: string | null;
}

export interface CourseSettingsConfig {
  source?: FileSourceConfig | null;
}

export interface CodeAbilityTestCommon {
  failureMessage?: string | null;
  successMessage?: string | null;
  qualification?: QualificationEnum | null;
  relativeTolerance?: number | null;
  absoluteTolerance?: number | null;
  allowedOccuranceRange?: number[] | null;
  occuranceType?: string | null;
  verbosity?: number | null;
}

export interface CodeAbilityTestCollectionCommon {
  failureMessage?: string | null;
  successMessage?: string | null;
  qualification?: QualificationEnum | null;
  relativeTolerance?: number | null;
  absoluteTolerance?: number | null;
  allowedOccuranceRange?: number[] | null;
  occuranceType?: string | null;
  verbosity?: number | null;
  storeGraphicsArtifacts?: boolean | null;
  competency?: string | null;
  timeout?: number | null;
}

export interface CodeAbilityTest {
  failureMessage?: string | null;
  successMessage?: string | null;
  qualification?: QualificationEnum | null;
  relativeTolerance?: number | null;
  absoluteTolerance?: number | null;
  allowedOccuranceRange?: number[] | null;
  occuranceType?: string | null;
  verbosity?: number | null;
  name: string;
  value?: any | null;
  evalString?: string | null;
  pattern?: string | null;
  countRequirement?: number | null;
}

export interface CodeAbilityTestCollection {
  failureMessage?: string | null;
  successMessage?: string | null;
  qualification?: QualificationEnum | null;
  relativeTolerance?: number | null;
  absoluteTolerance?: number | null;
  allowedOccuranceRange?: number[] | null;
  occuranceType?: string | null;
  verbosity?: number | null;
  storeGraphicsArtifacts?: boolean | null;
  competency?: string | null;
  timeout?: number | null;
  type?: TypeEnum | null;
  name: string;
  description?: string | null;
  successDependency?: (string | number | any[]) | null;
  setUpCodeDependency?: string | null;
  entryPoint?: string | null;
  inputAnswers?: (string | string[]) | null;
  setUpCode?: (string | string[]) | null;
  tearDownCode?: (string | string[]) | null;
  id?: string | null;
  file?: string | null;
  tests: CodeAbilityTest[];
}

export interface CodeAbilityTestProperty {
  failureMessage?: string | null;
  successMessage?: string | null;
  qualification?: QualificationEnum | null;
  relativeTolerance?: number | null;
  absoluteTolerance?: number | null;
  allowedOccuranceRange?: number[] | null;
  occuranceType?: string | null;
  verbosity?: number | null;
  storeGraphicsArtifacts?: boolean | null;
  competency?: string | null;
  timeout?: number | null;
  tests?: CodeAbilityTestCollection[];
}

export interface CodeAbilityTestSuite {
  type?: string | null;
  name?: string | null;
  description?: string | null;
  version?: string | null;
  properties?: CodeAbilityTestProperty;
}

export interface CodeAbilitySpecification {
  executionDirectory?: string | null;
  studentDirectory?: string | null;
  referenceDirectory?: string | null;
  testDirectory?: string | null;
  outputDirectory?: string | null;
  artifactDirectory?: string | null;
  testVersion?: string | null;
  storeGraphicsArtifacts?: boolean | null;
  outputName?: string | null;
  isLocalUsage?: boolean | null;
  studentTestCounter?: number | null;
}

export interface CodeAbilityMetaProperty {
  studentSubmissionFiles?: string[] | null;
  additionalFiles?: string[] | null;
  testFiles?: string[] | null;
  studentTemplates?: string[] | null;
  executionBackend?: CourseExecutionBackendConfig | null;
  maxTestRuns?: number | null;
  maxSubmissions?: number | null;
  maxGroupSize?: number | null;
}

export interface CodeAbilityReportSummary {
  total?: number;
  passed?: number;
  failed?: number;
  skipped?: number;
}

export interface CodeAbilityReleaseMeta {
  version?: string | null;
  kind?: MetaTypeEnum | null;
  title?: string | null;
  description?: string | null;
  language?: LanguageEnum | null;
  license?: string | null;
  authors?: CodeAbilityPerson[] | null;
  maintainers?: CodeAbilityPerson[] | null;
  links?: CodeAbilityLink[] | null;
  supportingMaterial?: CodeAbilityLink[] | null;
  keywords?: string[] | null;
  properties?: CodeAbilityMetaProperty | null;
}

export interface CodeAbilityCourseMeta {
  version?: string | null;
  kind?: MetaTypeEnum | null;
  title?: string | null;
  description?: string | null;
  language?: LanguageEnum | null;
  license?: string | null;
  authors?: CodeAbilityPerson[] | null;
  maintainers?: CodeAbilityPerson[] | null;
  links?: CodeAbilityLink[] | null;
  supportingMaterial?: CodeAbilityLink[] | null;
  keywords?: string[] | null;
  properties?: CodeAbilityMetaProperty | null;
  contentTypes?: TypeConfig[] | null;
  executionBackends?: CourseExecutionBackendConfig[] | null;
}

export interface CodeAbilityUnitMeta {
  version?: string | null;
  kind?: MetaTypeEnum | null;
  title?: string | null;
  description?: string | null;
  language?: LanguageEnum | null;
  license?: string | null;
  authors?: CodeAbilityPerson[] | null;
  maintainers?: CodeAbilityPerson[] | null;
  links?: CodeAbilityLink[] | null;
  supportingMaterial?: CodeAbilityLink[] | null;
  keywords?: string[] | null;
  properties?: CodeAbilityMetaProperty | null;
  type: string;
}

export interface CodeAbilityReportProperties {
  timestamp?: string | null;
  type?: string | null;
  version?: string | null;
  name?: string | null;
  description?: string | null;
  status?: StatusEnum | null;
  result?: ResultEnum | null;
  summary?: CodeAbilityReportSummary | null;
  statusMessage?: string | null;
  resultMessage?: string | null;
  details?: string | null;
  setup?: string | null;
  teardown?: string | null;
  duration?: number | null;
  executionDuration?: number | null;
  environment?: any | null;
  properties?: any | null;
  debug?: any | null;
}

export interface CodeAbilityReportSub {
  timestamp?: string | null;
  type?: string | null;
  version?: string | null;
  name?: string | null;
  description?: string | null;
  status?: StatusEnum | null;
  result?: ResultEnum | null;
  summary?: CodeAbilityReportSummary | null;
  statusMessage?: string | null;
  resultMessage?: string | null;
  details?: string | null;
  setup?: string | null;
  teardown?: string | null;
  duration?: number | null;
  executionDuration?: number | null;
  environment?: any | null;
  properties?: any | null;
  debug?: any | null;
}

export interface CodeAbilityReportMain {
  timestamp?: string | null;
  type?: string | null;
  version?: string | null;
  name?: string | null;
  description?: string | null;
  status?: StatusEnum | null;
  result?: ResultEnum | null;
  summary?: CodeAbilityReportSummary | null;
  statusMessage?: string | null;
  resultMessage?: string | null;
  details?: string | null;
  setup?: string | null;
  teardown?: string | null;
  duration?: number | null;
  executionDuration?: number | null;
  environment?: any | null;
  properties?: any | null;
  debug?: any | null;
  tests?: CodeAbilityReportSub[] | null;
}

export interface CodeAbilityReport {
  timestamp?: string | null;
  type?: string | null;
  version?: string | null;
  name?: string | null;
  description?: string | null;
  status?: StatusEnum | null;
  result?: ResultEnum | null;
  summary?: CodeAbilityReportSummary | null;
  statusMessage?: string | null;
  resultMessage?: string | null;
  details?: string | null;
  setup?: string | null;
  teardown?: string | null;
  duration?: number | null;
  executionDuration?: number | null;
  environment?: any | null;
  properties?: any | null;
  debug?: any | null;
  tests?: CodeAbilityReportMain[] | null;
}

/**
 * Semantic version following semver.org spec (subset).
 * 
 * Supports format: <major>.<minor>.<patch>[-<prerelease>]
 * 
 * Examples:
 * - 1.0.0
 * - 2.1.3
 * - 1.0.0-alpha
 * - 3.2.1-beta.2
 */
export interface SemanticVersion {
  /** Major version number */
  major: number;
  /** Minor version number */
  minor: number;
  /** Patch version number */
  patch: number;
  /** Optional prerelease identifier */
  prerelease?: any;
}

/**
 * Request to sync GitLab permissions for a course member.
 */
export interface GitLabSyncRequest {
  /** GitLab access token to check existing permissions before syncing (reduces API calls with organization token) */
  access_token?: string | null;
}

/**
 * Result of GitLab permission sync operation.
 */
export interface GitLabSyncResult {
  course_member_id: string;
  sync_status: string;
  message?: string | null;
}

/**
 * Optional configuration for tutor test (passed as JSON in form data).
 */
export interface TutorTestConfig {
  store_graphics_artifacts?: boolean;
  timeout_seconds?: number | null;
}

/**
 * Response when creating a tutor test - just the essentials.
 */
export interface TutorTestCreateResponse {
  test_id: string;
  status?: "pending" | "running" | "completed" | "failed" | "timeout";
  created_at?: string | null;
}

/**
 * Quick status check for a tutor test run (for polling).
 */
export interface TutorTestStatus {
  test_id: string;
  status: "pending" | "running" | "completed" | "failed" | "timeout";
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  has_artifacts?: boolean;
  artifact_count?: number;
}

/**
 * Full tutor test details including result_dict from MinIO.
 */
export interface TutorTestGet {
  test_id: string;
  status: "pending" | "running" | "completed" | "failed" | "timeout";
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  result_dict?: any | null;
  passed?: number | null;
  failed?: number | null;
  total?: number | null;
  result_value?: number | null;
  error?: string | null;
  has_artifacts?: boolean;
  artifact_count?: number;
}

/**
 * Information about a single artifact.
 */
export interface TutorTestArtifactInfo {
  filename: string;
  size: number;
  last_modified?: string | null;
}

/**
 * List of artifacts from a tutor test.
 */
export interface TutorTestArtifactList {
  test_id: string;
  artifacts?: TutorTestArtifactInfo[];
  total_count?: number;
}

/**
 * Member information in a submission group.
 */
export interface TutorSubmissionGroupMember {
  id: string;
  course_member_id: string;
  user_id: string;
  given_name?: string | null;
  family_name?: string | null;
  email?: string | null;
}

/**
 * List view of submission groups for tutors.
 */
export interface TutorSubmissionGroupList {
  id: string;
  course_id: string;
  course_content_id: string;
  display_name: string;
  max_group_size: number;
  max_submissions?: number | null;
  max_test_runs?: number | null;
  member_count?: number;
  submission_count?: number;
  latest_submission_at?: string | null;
  has_ungraded_submissions?: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Detailed view of a submission group for tutors.
 */
export interface TutorSubmissionGroupGet {
  id: string;
  course_id: string;
  course_content_id: string;
  display_name: string;
  max_group_size: number;
  max_submissions?: number | null;
  max_test_runs?: number | null;
  properties?: any | null;
  members?: TutorSubmissionGroupMember[];
  member_count?: number;
  submission_count?: number;
  test_run_count?: number;
  latest_submission_at?: string | null;
  latest_submission_id?: string | null;
  has_ungraded_submissions?: boolean;
  graded_submission_count?: number;
  latest_grade?: number | null;
  average_grade?: number | null;
  created_at: string;
  updated_at: string;
}

/**
 * Query parameters for filtering submission groups.
 */
export interface TutorSubmissionGroupQuery {
  course_id?: string | null;
  course_content_id?: string | null;
  course_group_id?: string | null;
  has_submissions?: boolean | null;
  has_ungraded_submissions?: boolean | null;
  limit?: number;
  offset?: number;
}

/**
 * Metadata for storage objects
 */
export interface StorageObjectMetadata {
  /** MIME type of the object */
  content_type: string;
  /** Size of the object in bytes */
  size: number;
  /** Entity tag of the object */
  etag: string;
  /** Last modification timestamp */
  last_modified: string;
  /** Custom metadata */
  metadata?: Record<string, string> | null;
}

/**
 * DTO for creating/uploading a storage object
 */
export interface StorageObjectCreate {
  /** Key/path for the object in the bucket */
  object_key: string;
  /** Target bucket name */
  bucket_name?: string | null;
  /** Custom metadata for the object */
  metadata?: Record<string, string> | null;
  /** MIME type of the object */
  content_type?: string | null;
}

/**
 * DTO for retrieving a storage object
 */
export interface StorageObjectGet {
  /** MIME type of the object */
  content_type: string;
  /** Size of the object in bytes */
  size: number;
  /** Entity tag of the object */
  etag: string;
  /** Last modification timestamp */
  last_modified: string;
  /** Custom metadata */
  metadata?: Record<string, string> | null;
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  /** Storage object ID */
  id: number;
  /** Object key/path in the bucket */
  object_key: string;
  /** Bucket name */
  bucket_name: string;
  /** Presigned download URL */
  download_url?: string | null;
}

/**
 * DTO for listing storage objects
 */
export interface StorageObjectList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  /** Storage object ID */
  id: number;
  /** Object key/path in the bucket */
  object_key: string;
  /** Bucket name */
  bucket_name: string;
  /** MIME type of the object */
  content_type: string;
  /** Size of the object in bytes */
  size: number;
  /** Last modification timestamp */
  last_modified: string;
}

/**
 * DTO for updating storage object metadata
 */
export interface StorageObjectUpdate {
  /** Updated custom metadata */
  metadata?: Record<string, string> | null;
  /** Updated MIME type */
  content_type?: string | null;
}

/**
 * Query parameters for filtering storage objects
 */
export interface StorageObjectQuery {
  skip?: number | null;
  limit?: number | null;
  /** Filter by bucket name */
  bucket_name?: string | null;
  /** Filter by object key prefix */
  prefix?: string | null;
  /** Filter by content type */
  content_type?: string | null;
  /** Minimum object size in bytes */
  min_size?: number | null;
  /** Maximum object size in bytes */
  max_size?: number | null;
}

/**
 * DTO for creating a storage bucket
 */
export interface BucketCreate {
  /** Name of the bucket to create */
  bucket_name: string;
  /** Region for the bucket */
  region?: string | null;
}

/**
 * DTO for bucket information
 */
export interface BucketInfo {
  /** Name of the bucket */
  bucket_name: string;
  /** Bucket creation date */
  creation_date?: string | null;
  /** Bucket region */
  region?: string | null;
}

/**
 * DTO for listing buckets
 */
export interface BucketList {
  /** List of buckets */
  buckets: BucketInfo[];
}

/**
 * DTO for generating presigned URLs
 */
export interface PresignedUrlRequest {
  /** Object key/path in the bucket */
  object_key: string;
  /** Bucket name */
  bucket_name?: string | null;
  /** URL expiry time in seconds */
  expiry_seconds?: number | null;
  /** HTTP method for the presigned URL */
  method?: string | null;
}

/**
 * DTO for presigned URL response
 */
export interface PresignedUrlResponse {
  /** The presigned URL */
  url: string;
  /** URL expiration timestamp */
  expires_at: string;
  /** HTTP method for the URL */
  method: string;
}

/**
 * DTO for storage usage statistics
 */
export interface StorageUsageStats {
  /** Bucket name */
  bucket_name: string;
  /** Number of objects in the bucket */
  object_count: number;
  /** Total size of all objects in bytes */
  total_size: number;
  /** Last statistics update timestamp */
  last_updated: string;
}

/**
 * DTO for creating a new service account.
 */
export interface ServiceCreate {
  /** URL-safe slug identifier (lowercase, alphanumeric, dots, hyphens) */
  slug: string;
  /** Human-readable service name */
  name: string;
  /** Service description */
  description?: string | null;
  /** Service type (e.g., 'temporal_worker', 'grading', 'notification') */
  service_type: string;
  /** Username for service user (defaults to slug) */
  username?: string | null;
  /** Email for service user */
  email?: string | null;
  /** Given name for service user (defaults to first word of name) */
  given_name?: string | null;
  /** Family name for service user (defaults to rest of name) */
  family_name?: string | null;
  /** Password for service user (optional - use API tokens instead) */
  password?: string | null;
  /** Service-specific configuration */
  config?: Record<string, any> | null;
  /** Whether the service is enabled */
  enabled?: boolean | null;
}

/**
 * DTO for updating a service account.
 */
export interface ServiceUpdate {
  name?: string | null;
  description?: string | null;
  config?: Record<string, any> | null;
  enabled?: boolean | null;
  /** Last heartbeat timestamp */
  last_seen_at?: string | null;
  properties?: Record<string, any> | null;
}

/**
 * DTO for retrieving a service account.
 */
export interface ServiceGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  /** Service UUID */
  id: string;
  slug: string;
  name: string;
  description?: string | null;
  /** ServiceType UUID */
  service_type_id?: string | null;
  /** ServiceType path (e.g., 'testing.python') */
  service_type_path?: string | null;
  user_id: string;
  config?: Record<string, any>;
  enabled: boolean;
  last_seen_at?: string | null;
  /** Additional properties */
  properties?: Record<string, any> | null;
}

/**
 * DTO for listing services.
 */
export interface ServiceList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  items: ServiceGet[];
}

/**
 * DTO for querying services.
 */
export interface ServiceQuery {
  skip?: number | null;
  limit?: number | null;
  /** Filter by service UUID */
  id?: string | null;
  /** Filter by service slug */
  slug?: string | null;
  /** Filter by service type UUID */
  service_type_id?: string | null;
  /** Filter by enabled status */
  enabled?: boolean | null;
  /** Filter by user ID */
  user_id?: string | null;
}

/**
 * Count of deleted entities by type.
 */
export interface EntityDeleteCount {
  courses?: number;
  course_families?: number;
  course_members?: number;
  course_groups?: number;
  course_content_types?: number;
  course_contents?: number;
  submission_groups?: number;
  submission_group_members?: number;
  submission_artifacts?: number;
  submission_grades?: number;
  submission_reviews?: number;
  results?: number;
  result_artifacts?: number;
  course_content_deployments?: number;
  deployment_histories?: number;
  course_member_comments?: number;
  messages?: number;
  example_repositories?: number;
  examples?: number;
  example_versions?: number;
  example_dependencies?: number;
  student_profiles?: number;
}

/**
 * Preview of what will be deleted in a cascade operation.
 */
export interface CascadeDeletePreview {
  /** Type of root entity being deleted */
  entity_type: string;
  /** ID of root entity being deleted */
  entity_id: string;
  /** Name/identifier of root entity */
  entity_name: string;
  /** Count of child entities that will be deleted */
  child_counts?: EntityDeleteCount;
  /** MinIO storage paths that will be cleaned up */
  minio_paths?: string[];
}

/**
 * Result of a cascade deletion operation.
 */
export interface CascadeDeleteResult {
  /** Whether this was a preview only */
  dry_run: boolean;
  /** Type of root entity deleted */
  entity_type: string;
  /** ID of root entity deleted */
  entity_id: string;
  /** Count of entities deleted by type */
  deleted_counts?: EntityDeleteCount;
  /** Number of MinIO objects deleted */
  minio_objects_deleted?: number;
  /** Errors encountered during deletion */
  errors?: string[];
}

export interface TestCreate {
  artifact_id?: string | null;
  submission_group_id?: string | null;
  version_identifier?: string | null;
  course_member_id?: string | null;
  course_content_id?: string | null;
  course_content_path?: string | null;
  directory?: string | null;
  project?: string | null;
  provider_url?: string | null;
  submit?: boolean | null;
}

/**
 * Payload describing a manual submission request.
 */
export interface SubmissionCreate {
  submission_group_id: string;
  version_identifier?: string | null;
  submit?: boolean;
}

/**
 * Metadata about a file extracted from a submission archive.
 */
export interface SubmissionUploadedFile {
  object_key: string;
  size: number;
  content_type: string;
  relative_path: string;
}

/**
 * Response returned after processing a manual submission.
 */
export interface SubmissionUploadResponseModel {
  artifacts: string[];
  submission_group_id: string;
  uploaded_by_course_member_id: string;
  total_size: number;
  files_count: number;
  uploaded_at: string;
  version_identifier: string;
}

/**
 * List item representation for manual submissions stored as results.
 */
export interface SubmissionListItem {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  id: string;
  submit: boolean;
  course_member_id: string;
  course_content_id: string;
  submission_group_id?: string | null;
  testing_service_id?: string | null;
  test_system_id?: string | null;
  version_identifier: string;
  reference_version_identifier?: string | null;
  status: TaskStatus;
  result: number;
  result_json?: Record<string, any> | null;
  properties?: Record<string, any> | null;
}

/**
 * Query parameters for listing manual submissions.
 */
export interface SubmissionQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  submit?: boolean | null;
  course_member_id?: string | null;
  submission_group_id?: string | null;
  course_content_id?: string | null;
  testing_service_id?: string | null;
  test_system_id?: string | null;
  version_identifier?: string | null;
  reference_version_identifier?: string | null;
  status?: TaskStatus | null;
}

export interface SessionCreate {
  /** Associated user ID */
  user_id: string;
  /** Hashed session token */
  session_id: string;
  /** Hashed refresh token (binary) */
  refresh_token_hash?: any | null;
  /** IP address at session creation */
  created_ip: string;
  /** Last seen IP address */
  last_ip?: string | null;
  /** User agent string */
  user_agent?: string | null;
  /** Human-readable device description */
  device_label?: string | null;
  /** Session expiration time */
  expires_at?: string | null;
  /** Refresh token expiration */
  refresh_expires_at?: string | null;
  /** Additional session properties */
  properties?: any | null;
}

export interface SessionGet {
  /** Session creation time */
  created_at: string;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  /** Session unique identifier */
  id: string;
  /** Unique session ID per device */
  sid: string;
  /** Associated user ID */
  user_id: string;
  /** Hashed session token */
  session_id: string;
  /** Last activity time */
  last_seen_at?: string | null;
  /** Expiration time */
  expires_at?: string | null;
  /** Revocation timestamp */
  revoked_at?: string | null;
  /** Reason for revocation */
  revocation_reason?: string | null;
  /** End timestamp (logout) */
  ended_at?: string | null;
  /** Number of token refreshes */
  refresh_counter?: number;
  /** IP at creation */
  created_ip: string;
  /** Last seen IP */
  last_ip?: string | null;
  /** Device description */
  device_label?: string | null;
  /** Additional properties */
  properties?: any | null;
  /** Deprecated: use ended_at */
  logout_time?: string | null;
  /** Deprecated: use created_ip */
  ip_address?: string | null;
}

export interface SessionList {
  /** Session creation time */
  created_at: string;
  /** Update timestamp */
  updated_at?: string | null;
  /** Session unique identifier */
  id: string;
  /** Unique session ID per device */
  sid: string;
  /** Associated user ID */
  user_id: string;
  /** Hashed session token */
  session_id: string;
  /** Last activity time */
  last_seen_at?: string | null;
  /** Expiration time */
  expires_at?: string | null;
  /** Revocation timestamp */
  revoked_at?: string | null;
  /** End timestamp */
  ended_at?: string | null;
  /** IP at creation */
  created_ip: string;
  /** Last seen IP */
  last_ip?: string | null;
  /** Device description */
  device_label?: string | null;
  /** Refresh count */
  refresh_counter?: number;
  /** Deprecated */
  logout_time?: string | null;
  /** Deprecated */
  ip_address?: string | null;
}

export interface SessionUpdate {
  /** Logout timestamp */
  logout_time?: string | null;
  /** Additional properties */
  properties?: any | null;
}

export interface SessionQuery {
  skip?: number | null;
  limit?: number | null;
  /** Filter by session ID */
  id?: string | null;
  /** Filter by user ID */
  user_id?: string | null;
  /** Filter by session identifier */
  session_id?: string | null;
  /** Filter for active sessions only */
  active_only?: boolean | null;
  /** Filter by IP address */
  ip_address?: string | null;
}

export interface GroupClaimCreate {
  /** Group ID this claim belongs to */
  group_id: string;
  /** Type of claim (e.g., 'permission', 'attribute') */
  claim_type: string;
  /** Value of the claim */
  claim_value: string;
  /** Additional claim properties */
  properties?: any | null;
}

export interface GroupClaimGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  /** Group ID */
  group_id: string;
  /** Type of claim */
  claim_type: string;
  /** Value of the claim */
  claim_value: string;
  /** Additional properties */
  properties?: any | null;
}

export interface GroupClaimList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  /** Group ID */
  group_id: string;
  /** Type of claim */
  claim_type: string;
  /** Value of the claim */
  claim_value: string;
}

export interface GroupClaimUpdate {
  /** Additional claim properties */
  properties?: any | null;
}

export interface GroupClaimQuery {
  skip?: number | null;
  limit?: number | null;
  /** Filter by group ID */
  group_id?: string | null;
  /** Filter by claim type */
  claim_type?: string | null;
  /** Filter by claim value */
  claim_value?: string | null;
}

/**
 * Information about a team member (for display in team lists).
 */
export interface TeamMemberInfo {
  course_member_id: string;
  user_id: string;
  given_name?: string | null;
  family_name?: string | null;
  email?: string | null;
}

/**
 * Team formation rules resolved from Course and CourseContent.
 */
export interface TeamFormationRules {
  mode?: string;
  max_group_size: number;
  min_group_size?: number;
  formation_deadline?: string | null;
  allow_student_group_creation?: boolean;
  allow_student_join_groups?: boolean;
  allow_student_leave_groups?: boolean;
  auto_assign_unmatched?: boolean;
  lock_teams_at_deadline?: boolean;
  require_approval?: boolean;
}

/**
 * Request to create a new team.
 */
export interface TeamCreate {
  /** Optional team name (default: generated from members) */
  team_name?: string | null;
}

/**
 * Response when team is created or retrieved.
 */
export interface TeamResponse {
  id: string;
  course_content_id: string;
  course_id: string;
  max_group_size: number;
  status?: string;
  created_by?: string;
  join_code?: string | null;
  members: TeamMemberInfo[];
  member_count: number;
  can_join: boolean;
  locked_at?: string | null;
}

/**
 * Team available for joining (limited info for privacy).
 */
export interface AvailableTeam {
  id: string;
  member_count: number;
  max_group_size: number;
  join_code?: string | null;
  requires_approval: boolean;
  status: string;
  members: TeamMemberInfo[];
}

/**
 * Request to join a team.
 */
export interface JoinTeamRequest {
  /** Optional join code for direct access */
  join_code?: string | null;
}

/**
 * Response when joining a team.
 */
export interface JoinTeamResponse {
  id: string;
  status: string;
  message: string;
}

/**
 * Response when leaving a team.
 */
export interface LeaveTeamResponse {
  success: boolean;
  message: string;
}

/**
 * Request to lock a team (instructor only).
 */
export interface TeamLockRequest {
  /** Optional reason for locking */
  reason?: string | null;
}

/**
 * Response when team is locked.
 */
export interface TeamLockResponse {
  id: string;
  locked_at: string;
  message: string;
}

/**
 * DTO for creating submission artifacts.
 * 
 * This is used internally when processing submission uploads.
 * The upload endpoint accepts SubmissionCreate which only has:
 * - submission_group_id
 * - version_identifier (optional)
 */
export interface SubmissionArtifactCreate {
  submission_group_id: string;
  version_identifier?: string | null;
}

/**
 * DTO for updating submission artifacts.
 */
export interface SubmissionArtifactUpdate {
  submit?: boolean | null;
  properties?: Record<string, any> | null;
}

/**
 * List item representation for submission artifacts.
 * 
 * Essential metadata is stored in proper database columns.
 * Properties field is kept for legacy compatibility and future extensibility.
 */
export interface SubmissionArtifactList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  id: string;
  submission_group_id: string;
  uploaded_by_course_member_id?: string | null;
  content_type?: string | null;
  file_size: number;
  bucket_name: string;
  object_key: string;
  uploaded_at: string;
  version_identifier?: string | null;
  submit?: boolean;
  properties?: Record<string, any> | null;
  latest_result?: ResultList | null;
}

/**
 * Detailed view of submission artifact with related data.
 */
export interface SubmissionArtifactGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  id: string;
  submission_group_id: string;
  uploaded_by_course_member_id?: string | null;
  content_type?: string | null;
  file_size: number;
  bucket_name: string;
  object_key: string;
  uploaded_at: string;
  version_identifier?: string | null;
  submit?: boolean;
  properties?: Record<string, any> | null;
  latest_result?: ResultList | null;
  test_results_count?: number | null;
  grades_count?: number | null;
  reviews_count?: number | null;
  average_grade?: number | null;
}

/**
 * Query parameters for listing submission artifacts.
 */
export interface SubmissionArtifactQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  submission_group_id?: string | null;
  uploaded_by_course_member_id?: string | null;
  content_type?: string | null;
  version_identifier?: string | null;
  submit?: boolean | null;
  latest?: boolean | null;
}

/**
 * DTO for creating submission grades.
 */
export interface SubmissionGradeCreate {
  artifact_id: string;
  graded_by_course_member_id: string;
  grade: number;
  status?: GradingStatus;
  comment?: string | null;
}

/**
 * DTO for updating submission grades.
 */
export interface SubmissionGradeUpdate {
  grade?: number | null;
  status?: GradingStatus | null;
  comment?: string | null;
}

/**
 * List item representation for submission grades.
 */
export interface SubmissionGradeList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  id: string;
  artifact_id: string;
  graded_by_course_member_id: string;
  grade: number;
  status: GradingStatus;
  comment?: string | null;
  graded_at: string;
}

/**
 * Detailed view of submission grade.
 */
export interface SubmissionGradeDetail {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  id: string;
  artifact_id: string;
  graded_by_course_member_id: string;
  grade: number;
  status: GradingStatus;
  comment?: string | null;
  graded_at: string;
}

/**
 * Query parameters for listing submission grades.
 */
export interface SubmissionGradeQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  artifact_id?: string | null;
  graded_by_course_member_id?: string | null;
  status?: GradingStatus | null;
  course_id?: string | null;
  latest?: boolean | null;
  start_date?: string | null;
  end_date?: string | null;
}

/**
 * DTO for creating submission reviews.
 */
export interface SubmissionReviewCreate {
  artifact_id: string;
  reviewer_course_member_id: string;
  body: string;
  review_type?: string | null;
}

/**
 * DTO for updating submission reviews.
 */
export interface SubmissionReviewUpdate {
  body?: string | null;
  review_type?: string | null;
}

/**
 * List item representation for submission reviews.
 */
export interface SubmissionReviewListItem {
  created_at: string;
  /** Update timestamp */
  updated_at?: string | null;
  id: string;
  artifact_id: string;
  reviewer_course_member_id: string;
  body: string;
  review_type?: string | null;
}

/**
 * Detailed view of submission review.
 */
export interface SubmissionReviewDetail {
  created_at: string;
  /** Update timestamp */
  updated_at?: string | null;
  id: string;
  artifact_id: string;
  reviewer_course_member_id: string;
  body: string;
  review_type?: string | null;
}

/**
 * Query parameters for listing submission reviews.
 */
export interface SubmissionReviewQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  artifact_id?: string | null;
  reviewer_course_member_id?: string | null;
  review_type?: string | null;
}

/**
 * DTO for creating result artifacts.
 */
export interface ResultArtifactCreate {
  result_id: string;
  content_type?: string | null;
  file_size: number;
  bucket_name: string;
  object_key: string;
  properties?: Record<string, any> | null;
}

/**
 * List item representation for result artifacts.
 */
export interface ResultArtifactListItem {
  created_at: string;
  /** Update timestamp */
  updated_at?: string | null;
  id: string;
  result_id: string;
  content_type?: string | null;
  file_size: number;
  bucket_name: string;
  object_key: string;
  properties?: Record<string, any> | null;
}

/**
 * Query parameters for listing result artifacts.
 */
export interface ResultArtifactQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  result_id?: string | null;
  content_type?: string | null;
}

/**
 * Information about a single uploaded artifact.
 */
export interface ArtifactInfo {
  filename: string;
  file_size: number;
  content_type?: string | null;
}

/**
 * Response for artifact upload endpoint.
 */
export interface ResultArtifactUploadResponse {
  result_id: string;
  artifacts_count: number;
  artifacts: ArtifactInfo[];
}

export interface CourseMemberGitLabConfig {
  settings?: any | null;
  url?: string | null;
  full_path?: string | null;
  directory?: string | null;
  registry?: string | null;
  parent?: number | null;
  group_id?: number | null;
  parent_id?: number | null;
  namespace_id?: number | null;
  namespace_path?: string | null;
  web_url?: string | null;
  visibility?: string | null;
  last_synced_at?: string | null;
  full_path_submission?: string | null;
}

export interface LanguageCreate {
  /** ISO 639-1 language code (2 lowercase letters) */
  code: string;
  /** Language name in English */
  name: string;
  /** Language name in native script */
  native_name?: string | null;
}

export interface LanguageGet {
  /** ISO 639-1 language code */
  code: string;
  /** Language name in English */
  name: string;
  /** Language name in native script */
  native_name?: string | null;
}

export interface LanguageList {
  /** ISO 639-1 language code */
  code: string;
  /** Language name in English */
  name: string;
  /** Language name in native script */
  native_name?: string | null;
}

export interface LanguageUpdate {
  /** Language name in English */
  name?: string | null;
  /** Language name in native script */
  native_name?: string | null;
}

export interface LanguageQuery {
  skip?: number | null;
  limit?: number | null;
  /** Filter by language code */
  code?: string | null;
  /** Filter by language name */
  name?: string | null;
  /** Filter by native language name */
  native_name?: string | null;
}

/**
 * Metadata stored with deployments.
 */
export interface DeploymentMetadata {
  /** Temporal workflow ID */
  workflow_id?: string | null;
  /** List of files deployed */
  files_deployed?: string[] | null;
  /** Git commit hash */
  git_commit?: string | null;
  /** Error details if deployment failed */
  error_details?: Record<string, any> | null;
  /** Properties migrated from old schema */
  migrated_properties?: Record<string, any> | null;
}

/**
 * Create a new deployment (typically done automatically).
 */
export interface CourseContentDeploymentCreate {
  /** Course content to deploy to */
  course_content_id: string;
  /** Example version to deploy */
  example_version_id: string;
  /** Initial deployment status */
  deployment_status?: "pending" | "deploying" | "deployed" | "failed" | "unassigned";
  /** Optional message */
  deployment_message?: string | null;
  /** Additional metadata */
  deployment_metadata?: DeploymentMetadata | null;
}

/**
 * Update deployment status.
 */
export interface CourseContentDeploymentUpdate {
  deployment_status?: "pending" | "deploying" | "deployed" | "failed" | "unassigned" | null;
  deployment_message?: string | null;
  deployed_at?: string | null;
  last_attempt_at?: string | null;
  deployment_path?: string | null;
  deployment_metadata?: DeploymentMetadata | null;
  example_identifier?: string | null;
  version_tag?: string | null;
}

/**
 * Get deployment details.
 */
export interface CourseContentDeploymentGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  course_content_id: string;
  example_version_id: string | null;
  example_identifier?: string | null;
  version_tag?: string | null;
  deployment_status: string;
  deployment_message?: string | null;
  assigned_at: string;
  deployed_at?: string | null;
  last_attempt_at?: string | null;
  deployment_path?: string | null;
  version_identifier?: string | null;
  deployment_metadata?: Record<string, any> | null;
  workflow_id?: string | null;
  example_version?: any | null;
}

/**
 * List view of deployments.
 */
export interface CourseContentDeploymentList {
  id: string;
  course_content_id: string;
  example_version_id: string | null;
  example_identifier?: string | null;
  version_tag?: string | null;
  deployment_status: string;
  assigned_at: string;
  deployed_at: string | null;
  version_identifier: string | null;
  example_version?: ExampleVersionList | null;
}

/**
 * Query parameters for deployments.
 */
export interface CourseContentDeploymentQuery {
  skip?: number | null;
  limit?: number | null;
  course_content_id?: string | null;
  example_version_id?: string | null;
  deployment_status?: string | null;
  deployed?: boolean | null;
  failed?: boolean | null;
}

/**
 * Create a deployment history entry.
 */
export interface DeploymentHistoryCreate {
  deployment_id: string;
  action: "assigned" | "reassigned" | "deploying" | "deployed" | "failed" | "unassigned" | "updated" | "migrated";
  example_version_id?: string | null;
  example_identifier?: string | null;
  version_tag?: string | null;
  previous_example_version_id?: string | null;
  workflow_id?: string | null;
}

/**
 * Get deployment history entry.
 */
export interface DeploymentHistoryGet {
  id: string;
  deployment_id: string;
  action: string;
  example_version_id: string | null;
  previous_example_version_id: string | null;
  example_identifier?: string | null;
  version_tag?: string | null;
  workflow_id: string | null;
  created_at: string;
  created_by: string | null;
  example_version?: any | null;
  previous_example_version?: any | null;
}

/**
 * List view of deployment history.
 */
export interface DeploymentHistoryList {
  id: string;
  deployment_id: string;
  action: string;
  created_at: string;
  workflow_id: string | null;
}

/**
 * Deployment with its full history.
 */
export interface DeploymentWithHistory {
  deployment: CourseContentDeploymentGet;
  history: DeploymentHistoryGet[];
}

/**
 * Summary of deployments for a course.
 */
export interface DeploymentSummary {
  course_id: string;
  /** Total course content items */
  total_content: number;
  /** Total submittable content (assignments) */
  submittable_content: number;
  /** Total deployments */
  deployments_total: number;
  /** Deployments pending */
  deployments_pending: number;
  /** Successfully deployed */
  deployments_deployed: number;
  /** Failed deployments */
  deployments_failed: number;
  /** Most recent deployment */
  last_deployment_at?: string | null;
}

/**
 * Request to assign an example to course content.
 */
export interface AssignExampleRequest {
  /** Example version to assign (optional if providing identifier+version_tag) */
  example_version_id?: string | null;
  /** Hierarchical identifier (ltree string) for the example source */
  example_identifier?: string | null;
  /** Version tag for the example source */
  version_tag?: string | null;
  /** Optional message about this assignment */
  deployment_message?: string | null;
}

/**
 * Request to deploy assigned examples.
 */
export interface DeployExampleRequest {
  /** Course to deploy examples for */
  course_id: string;
  /** Specific content IDs to deploy (all if None) */
  content_ids?: string[] | null;
  /** Force re-deployment even if already deployed */
  force?: boolean;
}

/**
 * GitLab connection credentials.
 */
export interface GitLabCredentials {
  gitlab_url: string;
  gitlab_token: string;
}

/**
 * Per-item override for release commit selection.
 */
export interface ReleaseOverride {
  course_content_id: string;
  /** Commit SHA to use for this content */
  version_identifier: string;
}

/**
 * Selection of contents and commits for a release.
 */
export interface ReleaseSelection {
  /** Explicit list of course content IDs to release */
  course_content_ids?: string[] | null;
  /** Parent content ID; combined with include_descendants */
  parent_id?: string | null;
  /** Whether to include descendants of parent_id */
  include_descendants?: boolean;
  /** Select all contents in the course */
  all?: boolean;
  /** Commit SHA to apply to all selected contents (overridden by per-item overrides) */
  global_commit?: string | null;
  /** Per-content commit overrides */
  overrides?: ReleaseOverride[] | null;
}

/**
 * Request to generate student template.
 */
export interface GenerateTemplateRequest {
  /** Custom commit message (optional) */
  commit_message?: string | null;
  /** Force redeployment of already deployed content */
  force_redeploy?: boolean;
  /** Selection of contents and commits to release */
  release?: ReleaseSelection | null;
}

/**
 * Response for template generation request.
 */
export interface GenerateTemplateResponse {
  workflow_id: string;
  status?: string;
  contents_to_process: number;
}

/**
 * Request to generate the assignments repository from Example Library.
 */
export interface GenerateAssignmentsRequest {
  assignments_url?: string | null;
  course_content_ids?: string[] | null;
  parent_id?: string | null;
  include_descendants?: boolean;
  all?: boolean;
  /** skip_if_exists|force_update */
  overwrite_strategy?: string;
  commit_message?: string | null;
}

export interface GenerateAssignmentsResponse {
  workflow_id: string;
  status?: string;
  contents_to_process: number;
}

/**
 * Complete error definition from registry.
 */
export interface ErrorDefinition {
  /** Unique error code (e.g., AUTH_001) */
  code: string;
  /** HTTP status code */
  http_status: number;
  /** Error category */
  category: ErrorCategory;
  /** Error severity */
  severity: ErrorSeverity;
  /** Short error title */
  title: string;
  /** Error messages in multiple formats */
  message: ErrorMessageFormat;
  /** Seconds to wait before retry */
  retry_after?: number | null;
  /** Link to documentation */
  documentation_url?: string | null;
  /** Internal description for developers */
  internal_description: string;
  /** Functions that may raise this error */
  affected_functions?: string[];
  /** Common causes of this error */
  common_causes?: string[];
  /** Steps to resolve the error */
  resolution_steps?: string[];
}

/**
 * Standard error response structure sent to clients.
 */
export interface ErrorResponse {
  /** Unique error code */
  error_code: string;
  /** Human-readable error message */
  message: string;
  /** Additional error details */
  details?: any | null;
  /** Error severity */
  severity: ErrorSeverity;
  /** Error category */
  category: ErrorCategory;
  /** Seconds to wait before retry */
  retry_after?: number | null;
  /** Link to documentation */
  documentation_url?: string | null;
  /** Debug information (dev mode only) */
  debug?: ErrorDebugInfo | null;
}

/**
 * Debug information included in development mode.
 */
export interface ErrorDebugInfo {
  /** ISO 8601 timestamp */
  timestamp: string;
  /** Request trace ID */
  request_id?: string | null;
  /** Function where error occurred */
  function?: string | null;
  /** File where error occurred */
  file?: string | null;
  /** Line number where error occurred */
  line?: number | null;
  /** User ID if authenticated */
  user_id?: string | null;
  /** Additional context */
  additional_context?: Record<string, any> | null;
}

/**
 * Metadata attached to exception instances for rich error handling.
 * 
 * This is used internally when raising exceptions to provide context.
 */
export interface ErrorMetadata {
  /** Error code from registry */
  error_code: string;
  /** Function raising the error */
  function_name?: string | null;
  /** Additional context */
  context?: Record<string, any>;
  /** User ID if available */
  user_id?: string | null;
  /** Request ID for tracing */
  request_id?: string | null;
  /** Override default message */
  override_message?: string | null;
  /** Override default details */
  override_details?: any | null;
}

export interface ResultCreate {
  course_member_id: string;
  course_content_id: string;
  submission_group_id?: string;
  submission_artifact_id?: string | null;
  testing_service_id?: string | null;
  test_system_id?: string | null;
  result: number;
  grade?: number | null;
  result_json?: any | null;
  properties?: any | null;
  version_identifier: string;
  reference_version_identifier?: string | null;
  status: TaskStatus;
}

/**
 * Artifact information embedded in ResultGet.
 */
export interface ResultArtifactInfo {
  id: string;
  filename: string;
  content_type?: string | null;
  file_size: number;
  created_at?: string | null;
}

export interface ResultGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  course_member_id: string;
  course_content_id: string;
  course_content_type_id: string;
  submission_group_id?: string | null;
  submission_artifact_id?: string | null;
  testing_service_id?: string | null;
  test_system_id?: string | null;
  result: number;
  grade?: number | null;
  result_json?: any | null;
  properties?: any | null;
  version_identifier: string;
  reference_version_identifier?: string | null;
  status: TaskStatus;
  grading_ids?: string[] | null;
  has_artifacts?: boolean;
  artifact_count?: number;
  result_artifacts?: ResultArtifactInfo[];
}

export interface ResultList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  id: string;
  course_member_id: string;
  course_content_id: string;
  course_content_type_id: string;
  submission_group_id?: string | null;
  submission_artifact_id?: string | null;
  testing_service_id?: string | null;
  test_system_id?: string | null;
  result: number;
  grade?: number | null;
  version_identifier: string;
  reference_version_identifier?: string | null;
  status: TaskStatus;
  has_artifacts?: boolean;
  artifact_count?: number;
}

export interface ResultUpdate {
  result?: number | null;
  grade?: number | null;
  result_json?: any | null;
  status?: TaskStatus | null;
  test_system_id?: string | null;
  properties?: any | null;
}

export interface ResultQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  submitter_id?: string | null;
  course_member_id?: string | null;
  course_content_id?: string | null;
  course_content_type_id?: string | null;
  submission_group_id?: string | null;
  submission_artifact_id?: string | null;
  testing_service_id?: string | null;
  test_system_id?: string | null;
  version_identifier?: string | null;
  status?: TaskStatus | null;
  latest?: boolean | null;
  result?: number | null;
  grade?: number | null;
}

/**
 * Result with associated grading information.
 */
export interface ResultWithGrading {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  course_member_id: string;
  course_content_id: string;
  course_content_type_id: string;
  submission_group_id?: string | null;
  submission_artifact_id?: string | null;
  testing_service_id?: string | null;
  test_system_id?: string | null;
  result: number;
  grade?: number | null;
  result_json?: any | null;
  properties?: any | null;
  version_identifier: string;
  reference_version_identifier?: string | null;
  status: TaskStatus;
  grading_ids?: string[] | null;
  has_artifacts?: boolean;
  artifact_count?: number;
  result_artifacts?: ResultArtifactInfo[];
  latest_grading?: any | null;
  grading_count?: number;
}

/**
 * Create a new grading for a submission group.
 */
export interface SubmissionGroupGradingCreate {
  submission_group_id: string;
  graded_by_course_member_id: string;
  result_id?: string | null;
  grading: number;
  status?: GradingStatus;
  feedback?: string | null;
  graded_by_course_member?: GradedByCourseMember | null;
}

/**
 * Full grading information.
 */
export interface SubmissionGroupGradingGet {
  created_at: string;
  updated_at: string;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  submission_group_id: string;
  graded_by_course_member_id: string;
  result_id?: string | null;
  grading: number;
  status: GradingStatus;
  feedback?: string | null;
  graded_by_course_member?: GradedByCourseMember | null;
}

/**
 * List view of grading.
 */
export interface SubmissionGroupGradingList {
  id: string;
  submission_group_id: string;
  graded_by_course_member_id: string;
  result_id?: string | null;
  grading: number;
  status: GradingStatus;
  feedback?: string | null;
  created_at: string;
  graded_by_course_member?: GradedByCourseMember | null;
}

/**
 * Update grading information.
 */
export interface SubmissionGroupGradingUpdate {
  grading?: number | null;
  status?: GradingStatus | null;
  feedback?: string | null;
  result_id?: string | null;
}

/**
 * Query parameters for searching gradings.
 */
export interface SubmissionGroupGradingQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  submission_group_id?: string | null;
  graded_by_course_member_id?: string | null;
  result_id?: string | null;
  status?: GradingStatus | null;
  min_grade?: number | null;
  max_grade?: number | null;
  has_feedback?: boolean | null;
}

/**
 * Simplified grading view for students.
 */
export interface GradingStudentView {
  id: string;
  grading: number;
  status: GradingStatus;
  feedback?: string | null;
  graded_by_name?: string | null;
  graded_at: string;
}

/**
 * Summary of gradings for a course content.
 */
export interface GradingSummary {
  course_content_id: string;
  total_submissions: number;
  graded_count: number;
  ungraded_count: number;
  corrected_count: number;
  correction_necessary_count: number;
  improvement_possible_count: number;
  average_grade?: number | null;
}

export interface GitCommit {
  hash: string;
  date: string;
  message: string;
  author: string;
}

/**
 * Credentials for GitLab Personal Access Token authentication.
 */
export interface GitLabPATCredentials {
  /** GitLab Personal Access Token (glpat-...) */
  access_token: string;
  /** GitLab instance URL (e.g., https://gitlab.com) */
  gitlab_url: string;
}

/**
 * Request to set password for first time or after reset.
 * 
 * Can authenticate either via:
 * 1. Bearer token (user already authenticated)
 * 2. Provider credentials (e.g., GitLab PAT for users without password)
 */
export interface SetPasswordRequest {
  /** New password (min 12 chars) */
  new_password: string;
  /** Confirm new password */
  confirm_password: string;
  /** Alternative authentication via external provider (for users without password) */
  provider_auth?: ProviderAuthCredentials | null;
}

/**
 * Request to change user's own password.
 */
export interface ChangePasswordRequest {
  /** Current password */
  old_password: string;
  /** New password (min 12 chars) */
  new_password: string;
  /** Confirm new password */
  confirm_password: string;
}

/**
 * Admin request to set another user's password.
 */
export interface AdminSetPasswordRequest {
  /** Target username */
  username: string;
  /** New password (min 12 chars) */
  new_password: string;
  /** Confirm new password */
  confirm_password: string;
  /** Require user to change password on next login */
  force_reset?: boolean;
}

/**
 * Admin request to reset a user's password (marks for reset).
 */
export interface AdminResetPasswordRequest {
  /** Target username */
  username: string;
}

/**
 * Response showing password status for a user.
 */
export interface PasswordStatusResponse {
  user_id: string;
  username: string;
  has_password: boolean;
  password_reset_required: boolean;
  password_type: string;
}

/**
 * Generic response for password operations.
 */
export interface PasswordOperationResponse {
  message: string;
  user_id: string;
  username: string;
}

export interface ProfileCreate {
  /** Associated user ID */
  user_id: string;
  /** Avatar color as RGB integer (0-16777215) */
  avatar_color?: number | null;
  /** Avatar image URL */
  avatar_image?: string | null;
  /** Unique nickname */
  nickname?: string | null;
  /** User biography */
  bio?: string | null;
  /** User website URL */
  url?: string | null;
  /** ISO 639-1 language code */
  language_code?: string | null;
  /** Additional profile properties */
  properties?: any | null;
}

export interface ProfileGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  /** Profile unique identifier */
  id: string;
  /** Associated user ID */
  user_id: string;
  /** Avatar color as RGB integer */
  avatar_color?: number | null;
  /** Avatar image URL */
  avatar_image?: string | null;
  /** Unique nickname */
  nickname?: string | null;
  /** User biography */
  bio?: string | null;
  /** User website URL */
  url?: string | null;
  /** ISO 639-1 language code */
  language_code?: string | null;
  /** Additional properties */
  properties?: any | null;
}

export interface ProfileList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  /** Profile unique identifier */
  id: string;
  /** Associated user ID */
  user_id: string;
  /** Unique nickname */
  nickname?: string | null;
  /** Avatar image URL */
  avatar_image?: string | null;
  /** Avatar color */
  avatar_color?: number | null;
  /** ISO 639-1 language code */
  language_code?: string | null;
}

export interface ProfileUpdate {
  /** Avatar color as RGB integer */
  avatar_color?: number | null;
  /** Avatar image URL */
  avatar_image?: string | null;
  /** Unique nickname */
  nickname?: string | null;
  /** User biography */
  bio?: string | null;
  /** User website URL */
  url?: string | null;
  /** ISO 639-1 language code */
  language_code?: string | null;
  /** Additional properties */
  properties?: any | null;
}

export interface ProfileQuery {
  skip?: number | null;
  limit?: number | null;
  /** Filter by profile ID */
  id?: string | null;
  /** Filter by user ID */
  user_id?: string | null;
  /** Filter by nickname */
  nickname?: string | null;
  /** Filter by language code */
  language_code?: string | null;
}

/**
 * DTO for creating a grade through the tutor endpoint.
 * 
 * This is used when a tutor grades a student's submission for a specific course content.
 * The endpoint will automatically find the latest artifact for the submission group.
 */
export interface TutorGradeCreate {
  artifact_id?: string | null;
  /** Grade between 0.0 and 1.0 */
  grade?: number | null;
  /** Grading status */
  status?: GradingStatus | null;
  /** Feedback/comment for the student */
  feedback?: string | null;
}

/**
 * Information about the artifact that was graded.
 * 
 * This provides context about which specific artifact received the grade,
 * useful for tracking grading history and artifact metadata.
 */
export interface GradedArtifactInfo {
  /** The artifact ID that was graded */
  id: string;
  /** When the artifact was created (ISO format) */
  created_at?: string | null;
  /** Additional artifact properties (e.g., GitLab info) */
  properties?: Record<string, any> | null;
}

/**
 * Response after creating a grade through the tutor endpoint.
 * 
 * Returns the updated course content information with the new grade applied.
 * We extend CourseContentStudentList to maintain backward compatibility.
 */
export interface TutorGradeResponse {
  id: string;
  title?: string | null;
  path: string;
  course_id: string;
  course_content_type_id: string;
  course_content_kind_id: string;
  position: number;
  max_group_size?: number | null;
  submitted?: boolean | null;
  course_content_type: CourseContentTypeList;
  result_count: number;
  submission_count: number;
  max_test_runs?: number | null;
  testing_service_id?: string | null;
  directory?: string | null;
  color: string;
  result?: ResultStudentList | null;
  submission_group?: SubmissionGroupStudentList | null;
  unread_message_count?: number;
  deployment?: CourseContentDeploymentList | null;
  has_deployment?: boolean | null;
  status?: string | null;
  unreviewed_count?: number;
  latest_grade_status?: string | null;
  graded_artifact_id?: string | null;
  graded_artifact_info?: GradedArtifactInfo | null;
}

/**
 * Single content item to validate.
 */
export interface ContentValidationItem {
  /** UUID of course content */
  content_id: string;
  /** Example identifier/slug from meta.yaml (dot-separated ltree path) */
  example_identifier: string;
  /** Version tag from meta.yaml (e.g., '1.0.0') */
  version_tag: string;
}

/**
 * Validation result for version existence.
 */
export interface VersionValidationResult {
  /** Version tag that was checked */
  version_tag: string;
  /** Whether the version exists */
  exists: boolean;
  /** Version ID if exists */
  version_id?: string | null;
  /** Error message if not exists */
  message?: string | null;
}

/**
 * Validation result for a single content item.
 */
export interface ContentValidationResult {
  content_id: string;
  /** Whether this content is valid overall */
  valid: boolean;
  example_validation: ExampleValidationResult;
  version_validation: VersionValidationResult;
  /** Overall validation message for this content */
  validation_message?: string | null;
}

/**
 * Request to validate multiple course contents - batch validation.
 */
export interface ContentValidationCreate {
  /** List of course content to validate */
  content_validations: ContentValidationItem[];
}

/**
 * Response from batch validation.
 */
export interface ContentValidationGet {
  /** Overall validation status */
  valid: boolean;
  /** Total items validated */
  total_validated: number;
  /** Number of issues found */
  total_issues: number;
  /** Validation results for each content item */
  validation_results: ContentValidationResult[];
}

/**
 * Metadata extracted from a VSIX manifest.
 */
export interface VsixMetadata {
  /** Publisher identifier from manifest */
  publisher: string;
  /** Extension name/ID from manifest */
  name: string;
  /** Semantic version from manifest */
  version: string;
  /** Display name from manifest */
  display_name?: string | null;
  /** Description from manifest */
  description?: string | null;
  /** VS Code engine compatibility range */
  engine_range?: string | null;
}

/**
 * Form metadata submitted when publishing a new extension version.
 */
export interface ExtensionPublishRequest {
  /** Semantic version override (defaults to manifest value) */
  version?: string | null;
  /** VS Code engine compatibility override */
  engine_range?: string | null;
  /** Friendly display name for the extension */
  display_name?: string | null;
  /** Optional extension description */
  description?: string | null;
}

/**
 * Common fields describing an extension version.
 */
export interface ExtensionVersionBase {
  /** Semantic version identifier */
  version: string;
  /** Sequential version number for ordering */
  version_number: number;
  /** VS Code engine compatibility constraint */
  engine_range?: string | null;
  /** Whether the version is yanked */
  yanked?: boolean;
  /** Package size in bytes */
  size: number;
  /** SHA256 checksum of the VSIX contents */
  sha256: string;
  /** Stored content type of the VSIX */
  content_type: string;
  /** Creation timestamp */
  created_at: string;
  /** Publish timestamp */
  published_at: string;
}

/**
 * List view of extension versions.
 */
export interface ExtensionVersionListItem {
  /** Semantic version identifier */
  version: string;
  /** Sequential version number for ordering */
  version_number: number;
  /** VS Code engine compatibility constraint */
  engine_range?: string | null;
  /** Whether the version is yanked */
  yanked?: boolean;
  /** Package size in bytes */
  size: number;
  /** SHA256 checksum of the VSIX contents */
  sha256: string;
  /** Stored content type of the VSIX */
  content_type: string;
  /** Creation timestamp */
  created_at: string;
  /** Publish timestamp */
  published_at: string;
}

/**
 * Detailed view of an extension version.
 */
export interface ExtensionVersionDetail {
  /** Semantic version identifier */
  version: string;
  /** Sequential version number for ordering */
  version_number: number;
  /** VS Code engine compatibility constraint */
  engine_range?: string | null;
  /** Whether the version is yanked */
  yanked?: boolean;
  /** Package size in bytes */
  size: number;
  /** SHA256 checksum of the VSIX contents */
  sha256: string;
  /** Stored content type of the VSIX */
  content_type: string;
  /** Creation timestamp */
  created_at: string;
  /** Publish timestamp */
  published_at: string;
  /** Object storage key for the VSIX */
  object_key: string;
}

/**
 * Response payload for version listing.
 */
export interface ExtensionVersionListResponse {
  items?: ExtensionVersionListItem[];
  /** Pagination cursor for the next page, if available */
  next_cursor?: string | null;
}

/**
 * Extension-level metadata including latest version information.
 */
export interface ExtensionMetadata {
  /** Publisher identifier */
  publisher: string;
  /** Extension name */
  name: string;
  /** Friendly display name for the extension */
  display_name?: string | null;
  /** Extension description */
  description?: string | null;
  /** Database identifier for the extension */
  id: string;
  /** Creation timestamp */
  created_at: string;
  /** Last update timestamp */
  updated_at: string;
  /** Number of stored versions */
  version_count: number;
  /** Metadata for the latest available version */
  latest_version?: ExtensionVersionListItem | null;
}

/**
 * Request payload to (un)yank a specific version.
 */
export interface ExtensionVersionYankRequest {
  /** Target yank state for the version */
  yanked: boolean;
}

/**
 * Response payload returned after publishing a version.
 */
export interface ExtensionPublishResponse {
  /** Semantic version identifier */
  version: string;
  /** Sequential version number for ordering */
  version_number: number;
  /** VS Code engine compatibility constraint */
  engine_range?: string | null;
  /** Whether the version is yanked */
  yanked?: boolean;
  /** Package size in bytes */
  size: number;
  /** SHA256 checksum of the VSIX contents */
  sha256: string;
  /** Stored content type of the VSIX */
  content_type: string;
  /** Creation timestamp */
  created_at: string;
  /** Publish timestamp */
  published_at: string;
  /** Object storage key for the VSIX */
  object_key: string;
  /** Publisher identifier */
  publisher: string;
  /** Extension name */
  name: string;
}

/**
 * Response after assigning an example.
 */
export interface AssignExampleResponse {
  /** ID of the deployment record */
  deployment_id: string;
  course_content_id: string;
  example_id: string;
  example_version_id: string;
  version_tag: string;
  /** Status: 'pending' */
  deployment_status: string;
  assigned_at: string;
  /** Success message */
  message: string;
}

/**
 * Detailed deployment information for a course content.
 */
export interface DeploymentGet {
  id: string;
  course_content_id: string;
  example_id?: string | null;
  example_version_id?: string | null;
  example_identifier?: string | null;
  version_tag?: string | null;
  deployment_status: string;
  deployment_message?: string | null;
  assigned_at: string;
  deployed_at?: string | null;
  deployment_path?: string | null;
  example_title?: string | null;
  example_directory?: string | null;
  example_description?: string | null;
  course_content_title?: string | null;
  course_content_path?: string | null;
}

/**
 * Minimal deployment info for list views.
 */
export interface DeploymentList {
  id: string;
  course_content_id: string;
  deployment_status: string;
  version_tag?: string | null;
  assigned_at: string;
  deployed_at?: string | null;
}

/**
 * Response after unassigning an example.
 */
export interface UnassignExampleResponse {
  course_content_id: string;
  /** Success message */
  message: string;
  previous_example_id?: string | null;
  previous_version_tag?: string | null;
}

/**
 * Single validation error for release validation.
 */
export interface ValidationError {
  course_content_id: string;
  title: string;
  path: string;
  issue: string;
}

/**
 * Error response when release validation fails.
 */
export interface ReleaseValidationError {
  /** Main error message */
  error: string;
  /** List of specific issues */
  validation_errors: ValidationError[];
  /** Count of validation errors */
  total_issues: number;
}

export interface SubmissionGroupMemberProperties {
  gitlab?: GitLabConfig | null;
}

export interface SubmissionGroupMemberCreate {
  course_member_id: string;
  submission_group_id: string;
  grading?: number | null;
  properties?: SubmissionGroupMemberProperties | null;
}

export interface SubmissionGroupMemberGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  course_id: string;
  course_member_id: string;
  submission_group_id: string;
  grading?: number | null;
  status?: string | null;
  properties?: SubmissionGroupMemberProperties | null;
}

export interface SubmissionGroupMemberList {
  id: string;
  course_id: string;
  course_member_id: string;
  submission_group_id: string;
  grading?: number | null;
  status?: string | null;
}

export interface SubmissionGroupMemberUpdate {
  course_id?: string | null;
  grading?: number | null;
  status?: string | null;
  properties?: SubmissionGroupMemberProperties | null;
}

export interface SubmissionGroupMemberQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  course_id?: string | null;
  course_content_id?: string | null;
  course_member_id?: string | null;
  submission_group_id?: string | null;
  grading?: number | null;
  status?: string | null;
}



export type GroupType = "fixed" | "dynamic";

export type MergeMethod = "rebase_merge" | "merge" | "ff";

export type StatusEnum = "SCHEDULED" | "COMPLETED" | "TIMEDOUT" | "CRASHED" | "CANCELLED" | "SKIPPED" | "FAILED";

export type ResultEnum = "PASSED" | "FAILED" | "SKIPPED";

export type QualificationEnum = "verifyEqual" | "matches" | "contains" | "startsWith" | "endsWith" | "count" | "regexp";

export type TypeEnum = "variable" | "graphics" | "structural" | "linting" | "exist" | "error" | "warning" | "help" | "stdout";

export type LanguageEnum = "de" | "en";

export type MetaTypeEnum = "course" | "unit" | "assignment";

export type ForceLevel = "none" | "old" | "all";

export type ErrorSeverity = "info" | "warning" | "error" | "critical";

export type ErrorCategory = "authentication" | "authorization" | "validation" | "not_found" | "conflict" | "rate_limit" | "external_service" | "database" | "internal" | "not_implemented";

export type GradingStatus = 0 | 1 | 2 | 3;

export type ErrorCode = "AUTH_001" | "AUTH_002" | "AUTH_003" | "AUTH_004" | "AUTHZ_001" | "AUTHZ_002" | "AUTHZ_003" | "AUTHZ_004" | "AUTHZ_005" | "VAL_001" | "VAL_002" | "VAL_003" | "VAL_004" | "NF_001" | "NF_002" | "NF_003" | "NF_004" | "CONFLICT_001" | "CONFLICT_002" | "RATE_001" | "RATE_002" | "RATE_003" | "CONTENT_001" | "CONTENT_002" | "CONTENT_003" | "CONTENT_004" | "CONTENT_005" | "VERSION_001" | "DEPLOY_001" | "DEPLOY_002" | "DEPLOY_003" | "DEPLOY_004" | "SUBMIT_001" | "SUBMIT_002" | "SUBMIT_003" | "SUBMIT_004" | "SUBMIT_005" | "SUBMIT_006" | "SUBMIT_007" | "SUBMIT_008" | "TASK_001" | "TASK_002" | "TASK_003" | "TASK_004" | "GITLAB_001" | "GITLAB_002" | "GITLAB_003" | "GITLAB_004" | "GITLAB_005" | "GITLAB_006" | "GITLAB_007" | "GITLAB_008" | "EXT_001" | "EXT_002" | "EXT_003" | "EXT_004" | "EXT_005" | "DB_001" | "DB_002" | "DB_003" | "INT_001" | "INT_002" | "NIMPL_001";