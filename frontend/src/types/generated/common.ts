/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Common

 */



import type { CourseExecutionBackendConfig, CourseSignupResponse } from './courses';

import type { ExampleVersionList } from './examples';

import type { TaskStatus } from './tasks';

import type { UserGet } from './users';



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

export interface Repository {
  url: string;
  user?: string | null;
  token?: string | null;
  branch?: string | null;
  path?: string | null;
  commit?: string | null;
}

export interface StudentProfileCreate {
  id?: string | null;
  student_id?: string | null;
  student_email?: string | null;
  user_id?: string | null;
}

export interface StudentProfileGet {
  id: string;
  student_id?: string | null;
  student_email?: string | null;
  user_id: string;
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
}

export interface StudentProfileList {
  id: string;
  student_id?: string | null;
  student_email?: string | null;
  user_id: string;
}

export interface StudentProfileUpdate {
  student_id?: string | null;
  student_email?: string | null;
  properties?: any | null;
}

export interface StudentProfileQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  student_id?: string | null;
  student_email?: string | null;
  user_id?: string | null;
  properties?: any | null;
}

/**
 * Payload describing a manual submission request.
 */
export interface SubmissionCreate {
  course_submission_group_id: string;
  version_identifier?: string | null;
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
  result_id: string;
  bucket_name: string;
  files: SubmissionUploadedFile[];
  total_size: number;
  submitted_at: string;
  version_identifier: string;
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
  deployment_status?: any;
  /** Optional message */
  deployment_message?: string | null;
  /** Additional metadata */
  deployment_metadata?: DeploymentMetadata | null;
}

/**
 * Update deployment status.
 */
export interface CourseContentDeploymentUpdate {
  deployment_status?: any | null;
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
  deployment_message: string | null;
  assigned_at: string;
  deployed_at: string | null;
  last_attempt_at: string | null;
  deployment_path: string | null;
  version_identifier: string | null;
  deployment_metadata: Record<string, any> | null;
  workflow_id: string | null;
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
  action: any;
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

export interface ExecutionBackendCreate {
  type: string;
  slug: string;
  properties?: any | null;
}

export interface ExecutionBackendGet {
  type: string;
  slug: string;
  properties?: any | null;
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
}

export interface ExecutionBackendList {
  type: string;
  slug: string;
  properties?: any | null;
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
}

export interface ExecutionBackendUpdate {
  type?: string | null;
  slug?: string | null;
  properties?: any | null;
}

export interface ExecutionBackendQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  type?: string | null;
  slug?: string | null;
  properties?: string | null;
}

export interface Claims {
  general?: any;
  dependent?: any;
}

export interface Principal {
  is_admin?: boolean;
  user_id?: string | null;
  roles?: string[];
  claims?: Claims;
}

export interface GroupCreate {
  /** Group name */
  name: string;
  /** Group description */
  description?: string | null;
  /** Type of group (fixed or dynamic) */
  group_type: GroupType;
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
  /** Group name */
  name: string;
  /** Group description */
  description?: string | null;
  /** Type of group */
  group_type: GroupType;
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
  /** Group name */
  name: string;
  /** Group description */
  description?: string | null;
  /** Type of group */
  group_type: GroupType;
}

export interface GroupUpdate {
  /** Group name */
  name?: string | null;
  /** Group description */
  description?: string | null;
  /** Type of group */
  group_type?: GroupType | null;
  /** Additional properties */
  properties?: any | null;
}

export interface GroupQuery {
  skip?: number | null;
  limit?: number | null;
  /** Filter by group ID */
  id?: string | null;
  /** Filter by group name */
  name?: string | null;
  /** Filter by group type */
  group_type?: GroupType | null;
  /** Filter by archived status */
  archived?: boolean | null;
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

export interface StudentTemplateSettings {
  mr_default_target_self?: boolean;
  merge_method?: MergeMethod;
  only_allow_merge_if_pipeline_succeeds?: boolean;
  only_allow_merge_if_all_discussions_are_resolved?: boolean;
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

export interface ResultCreate {
  submit: boolean;
  course_member_id: string;
  course_content_id: string;
  course_submission_group_id?: string;
  execution_backend_id?: string | null;
  test_system_id?: string | null;
  result: number;
  result_json?: any | null;
  properties?: any | null;
  version_identifier: string;
  reference_version_identifier?: string | null;
  status: TaskStatus;
}

export interface ResultGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  submit: boolean;
  course_member_id: string;
  course_content_id: string;
  course_content_type_id: string;
  course_submission_group_id?: string | null;
  execution_backend_id?: string | null;
  test_system_id?: string | null;
  result: number;
  result_json?: any | null;
  properties?: any | null;
  version_identifier: string;
  reference_version_identifier?: string | null;
  status: TaskStatus;
  grading_ids?: string[] | null;
}

export interface ResultList {
  id: string;
  submit: boolean;
  course_member_id: string;
  course_content_id: string;
  course_content_type_id: string;
  course_submission_group_id?: string | null;
  execution_backend_id?: string | null;
  test_system_id?: string | null;
  result: number;
  version_identifier: string;
  reference_version_identifier?: string | null;
  status: TaskStatus;
}

export interface ResultUpdate {
  submit?: boolean | null;
  result?: number | null;
  result_json?: any | null;
  status?: TaskStatus | null;
  test_system_id?: string | null;
  properties?: any | null;
}

export interface ResultQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  submit?: boolean | null;
  submitter_id?: string | null;
  course_member_id?: string | null;
  course_content_id?: string | null;
  course_content_type_id?: string | null;
  course_submission_group_id?: string | null;
  execution_backend_id?: string | null;
  test_system_id?: string | null;
  version_identifier?: string | null;
  status?: TaskStatus | null;
  latest?: boolean | null;
  result?: number | null;
  result_json?: string | null;
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
  submit: boolean;
  course_member_id: string;
  course_content_id: string;
  course_content_type_id: string;
  course_submission_group_id?: string | null;
  execution_backend_id?: string | null;
  test_system_id?: string | null;
  result: number;
  result_json?: any | null;
  properties?: any | null;
  version_identifier: string;
  reference_version_identifier?: string | null;
  status: TaskStatus;
  grading_ids?: string[] | null;
  latest_grading?: any | null;
  grading_count?: number;
}

/**
 * Detailed result information including submission group and grading.
 */
export interface ResultDetailed {
  id: string;
  submit: boolean;
  course_member_id: string;
  course_member_name?: string | null;
  course_content_id: string;
  course_content_title?: string | null;
  course_content_path?: string | null;
  course_content_type_id: string;
  course_submission_group_id?: string | null;
  submission_group_members?: any[] | null;
  execution_backend_id: string;
  test_system_id?: string | null;
  result: number;
  result_json?: any | null;
  properties?: any | null;
  version_identifier: string;
  reference_version_identifier?: string | null;
  status: TaskStatus;
  gradings?: any[];
  latest_grade?: number | null;
  latest_grading_status?: number | null;
  latest_grading_feedback?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
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

export interface TestCreate {
  course_member_id?: string | null;
  course_content_id?: string | null;
  course_content_path?: string | null;
  directory?: string | null;
  project?: string | null;
  provider_url?: string | null;
  version_identifier?: string | null;
  submit?: boolean | null;
}

export interface SessionCreate {
  /** Associated user ID */
  user_id: string;
  /** Session identifier/token */
  session_id: string;
  /** IP address of the session */
  ip_address: string;
  /** Additional session properties */
  properties?: any | null;
}

export interface SessionGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  /** Session unique identifier */
  id: string;
  /** Associated user ID */
  user_id: string;
  /** Session identifier/token */
  session_id: string;
  /** Logout timestamp */
  logout_time?: string | null;
  /** IP address */
  ip_address: string;
  /** Additional properties */
  properties?: any | null;
}

export interface SessionList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  /** Session unique identifier */
  id: string;
  /** Associated user ID */
  user_id: string;
  /** Session identifier/token */
  session_id: string;
  /** Logout timestamp */
  logout_time?: string | null;
  /** IP address */
  ip_address: string;
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
 * DTO for creating a student.
 */
export interface StudentCreate {
  user_id?: (string | string) | null;
  user?: UserGet | null;
  course_group_id?: (string | string) | null;
  course_group_title?: string | null;
  role?: string | null;
}

/**
 * DTO for releasing multiple students.
 */
export interface ReleaseStudentsCreate {
  students?: StudentCreate[];
  course_id: any;
}

/**
 * DTO for TUG student export data.
 */
export interface TUGStudentExport {
  course_group_title: string;
  family_name: string;
  given_name: string;
  matriculation_number: string;
  created_at: string;
}

/**
 * DTO for status query parameters.
 */
export interface StatusQuery {
  course_id?: string | null;
}

/**
 * GitLab connection credentials.
 */
export interface GitLabCredentials {
  gitlab_url: string;
  gitlab_token: string;
}

/**
 * Represents a pending change for template generation.
 */
export interface PendingChange {
  /** new, update, remove */
  type: string;
  content_id: string;
  path: string;
  title: string;
}

/**
 * Response for pending changes check.
 */
export interface PendingChangesResponse {
  total_changes: number;
  changes: PendingChange[];
  last_release?: Record<string, any> | null;
}

/**
 * Per-item override for release commit selection.
 */
export interface ReleaseOverride {
  course_content_id: any;
  /** Commit SHA to use for this content */
  version_identifier: string;
}

/**
 * Selection of contents and commits for a release.
 */
export interface ReleaseSelection {
  /** Explicit list of course content IDs to release */
  course_content_ids?: any[] | null;
  /** Parent content ID; combined with include_descendants */
  parent_id?: (string | string) | null;
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

export interface GitCommit {
  hash: string;
  date: string;
  message: string;
  author: string;
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

export interface SubmissionGroupProperties {
  gitlab?: GitLabConfig | null;
}

export interface SubmissionGroupCreate {
  properties?: SubmissionGroupProperties | null;
  max_group_size?: number;
  max_submissions?: number | null;
  course_content_id: string;
  status?: string | null;
}

export interface SubmissionGroupGet {
  properties?: SubmissionGroupProperties | null;
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
  max_group_size: number;
  max_submissions?: number | null;
  course_id: string;
  course_content_id: string;
  status?: string | null;
  last_submitted_result_id?: string | null;
}

export interface SubmissionGroupUpdate {
  properties?: SubmissionGroupProperties | null;
  max_group_size?: number | null;
  max_submissions?: number | null;
  status?: string | null;
}

export interface SubmissionGroupQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
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

export interface SubmissionGroupMemberProperties {
  gitlab?: GitLabConfig | null;
}

export interface SubmissionGroupMemberCreate {
  course_member_id: string;
  course_submission_group_id: string;
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
  course_content_id: string;
  course_member_id: string;
  course_submission_group_id: string;
  grading?: number | null;
  status?: string | null;
  properties?: SubmissionGroupMemberProperties | null;
}

export interface SubmissionGroupMemberList {
  id: string;
  course_id: string;
  course_content_id: string;
  course_member_id: string;
  course_submission_group_id: string;
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
  course_submission_group_id?: string | null;
  grading?: number | null;
  status?: string | null;
  properties?: SubmissionGroupMemberProperties | null;
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
  /** References to execution backends to link to this course (by slug) */
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
  /** References to execution backends to link to this course (by slug) */
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
  /** List of execution backends to create or ensure exist in the system */
  execution_backends?: ExecutionBackendConfig[] | null;
  /** List of organizations with nested course families and courses */
  organizations: HierarchicalOrganizationConfig[];
  /** List of users with their accounts and course memberships */
  users?: UserAccountDeployment[];
  /** Global deployment settings */
  settings?: Record<string, any> | null;
  /** If provided, uploads examples before hierarchy deployment */
  examples_upload?: ExamplesUploadConfig | null;
}

export interface ExamplesUploadConfig {
  /** Name of the Example Repository to use/create */
  repository: string;
  /** Relative path to directory containing example subdirectories */
  path: string;
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

export interface VSCExtensionConfig {
  project_id: number;
  gitlab_url: string;
  file_path: string;
  download_link: string;
}

export interface TestRunResponse {
  submit: boolean;
  course_member_id: string;
  course_content_id: string;
  course_submission_group_id?: string;
  execution_backend_id?: string | null;
  test_system_id?: string | null;
  result: number;
  result_json?: any | null;
  properties?: any | null;
  version_identifier: string;
  reference_version_identifier?: string | null;
  status: TaskStatus;
  id: string;
}

export interface GitlabSignup {
  provider: string;
  token: string;
}

export interface GitlabSignupResponse {
  courses?: CourseSignupResponse[];
}

/**
 * Request model for creating a merge request submission.
 */
export interface SubmitRequest {
  /** The branch name to create merge request from */
  branch_name: string;
  /** GitLab Personal Access Token for authentication */
  gitlab_token: string;
  /** Optional title for the merge request */
  title?: string | null;
  /** Optional description for the merge request */
  description?: string | null;
}

/**
 * Response model for merge request submission.
 */
export interface SubmitResponse {
  /** The ID of the created merge request */
  merge_request_id: number;
  /** The internal ID of the merge request */
  merge_request_iid: number;
  /** The web URL of the merge request */
  web_url: string;
  /** The source branch of the merge request */
  source_branch: string;
  /** The target branch of the merge request */
  target_branch: string;
  /** The title of the merge request */
  title: string;
  /** The state of the merge request */
  state: string;
}



export type GroupType = "fixed" | "dynamic";

export type MergeMethod = "rebase_merge" | "merge" | "ff";

export type GradingStatus = 0 | 1 | 2 | 3;

export type StatusEnum = "SCHEDULED" | "COMPLETED" | "TIMEDOUT" | "CRASHED" | "CANCELLED" | "SKIPPED" | "FAILED";

export type ResultEnum = "PASSED" | "FAILED" | "SKIPPED";

export type QualificationEnum = "verifyEqual" | "matches" | "contains" | "startsWith" | "endsWith" | "count" | "regexp";

export type TypeEnum = "variable" | "graphics" | "structural" | "linting" | "exist" | "error" | "warning" | "help" | "stdout";

export type LanguageEnum = "de" | "en";

export type MetaTypeEnum = "course" | "unit" | "assignment";