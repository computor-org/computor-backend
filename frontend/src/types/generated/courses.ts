/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Courses

 */



import type { GradingAuthor } from './auth';

import type { ComputorDeploymentConfig, CourseContentDeploymentGet, CourseContentDeploymentList, CourseMemberGitLabConfig, GitLabConfig, GitLabConfigGet, GitLabCredentials, GradingStatus } from './common';

import type { OrganizationGet } from './organizations';

import type { TaskStatus } from './tasks';

import type { UserList } from './users';



export interface TutorCourseMemberCourseContent {
  id: string;
  path: string;
}

export interface TutorCourseMemberGet {
  id: string;
  properties?: CourseMemberProperties | null;
  user_id: string;
  course_id: string;
  course_group_id?: string | null;
  course_role_id: string;
  unreviewed_course_contents?: TutorCourseMemberCourseContent[];
  user: UserList;
}

export interface TutorCourseMemberList {
  id: string;
  user_id: string;
  course_id: string;
  course_group_id?: string | null;
  course_role_id: string;
  unreviewed?: boolean | null;
  user: UserList;
}

/**
 * Readiness state for a course member to start working on provider-backed tasks.
 */
export interface CourseMemberReadinessStatus {
  course_member_id: string;
  course_id: string;
  organization_id: string;
  course_role_id: string;
  provider_type?: string | null;
  provider?: string | null;
  requires_account: boolean;
  has_account: boolean;
  is_ready: boolean;
  provider_account_id?: string | null;
}

export interface CourseProperties {
  gitlab?: GitLabConfig | null;
}

export interface CoursePropertiesGet {
  gitlab?: GitLabConfigGet | null;
}

export interface CourseCreate {
  id?: string | null;
  title?: string | null;
  description?: string | null;
  path: string;
  course_family_id: string;
  properties?: CourseProperties | null;
}

export interface CourseGet {
  id: string;
  title?: string | null;
  description?: string | null;
  path: string;
  course_family_id: string;
  properties?: CoursePropertiesGet | null;
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  organization_id: string;
  course_family?: CourseFamilyGet | null;
}

export interface CourseList {
  id: string;
  title?: string | null;
  course_family_id?: string | null;
  organization_id?: string | null;
  path: string;
  properties?: CoursePropertiesGet | null;
}

export interface CourseUpdate {
  title?: string | null;
  description?: string | null;
  properties?: CourseProperties | null;
}

export interface CourseQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  title?: string | null;
  description?: string | null;
  path?: string | null;
  course_family_id?: string | null;
  organization_id?: string | null;
  provider_url?: string | null;
  full_path?: string | null;
}

export interface CourseMemberProperties {
  gitlab?: CourseMemberGitLabConfig | null;
}

export interface CourseMemberCreate {
  id?: string | null;
  properties?: CourseMemberProperties | null;
  user_id: string;
  course_id: string;
  course_group_id?: string | null;
  course_role_id: string;
}

export interface CourseMemberGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  properties?: CourseMemberProperties | null;
  user_id: string;
  course_id: string;
  course_group_id?: string | null;
  course_role_id: string;
  user?: UserList | null;
}

export interface CourseMemberList {
  id: string;
  user_id: string;
  course_id: string;
  course_group_id?: string | null;
  course_role_id: string;
  user: UserList;
}

export interface CourseMemberUpdate {
  properties?: CourseMemberProperties | null;
  course_group_id?: string | null;
  course_role_id?: string | null;
}

export interface CourseMemberQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  user_id?: string | null;
  course_id?: string | null;
  course_group_id?: string | null;
  course_role_id?: string | null;
  properties?: CourseMemberProperties | null;
  given_name?: string | null;
  family_name?: string | null;
}

export interface CourseExecutionBackendCreate {
  execution_backend_id: string;
  course_id: string;
  properties?: any | null;
}

export interface CourseExecutionBackendGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  execution_backend_id: string;
  course_id: string;
  properties?: any | null;
}

export interface CourseExecutionBackendList {
  execution_backend_id: string;
  course_id: string;
}

export interface CourseExecutionBackendUpdate {
  properties?: any | null;
}

export interface CourseExecutionBackendQuery {
  skip?: number | null;
  limit?: number | null;
  execution_backend_id?: string | null;
  course_id?: string | null;
  properties?: string | null;
}

export interface CourseRoleGet {
  id: string;
  title?: string | null;
  description?: string | null;
}

export interface CourseRoleList {
  id: string;
  title?: string | null;
  description?: string | null;
}

export interface CourseRoleQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  title?: string | null;
  description?: string | null;
}

export interface CourseContentTypeCreate {
  slug: string;
  title?: string | null;
  description?: string | null;
  color?: string | null;
  properties?: any | null;
  course_id: string;
  course_content_kind_id: string;
}

export interface CourseContentTypeGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  slug: string;
  title?: string | null;
  description?: string | null;
  color: string;
  properties?: any | null;
  course_id: string;
  course_content_kind_id: string;
  course_content_kind?: CourseContentKindGet | null;
}

export interface CourseContentTypeList {
  id: string;
  slug: string;
  title?: string | null;
  color: string;
  course_id: string;
  course_content_kind_id: string;
  course_content_kind?: CourseContentKindList | null;
}

export interface CourseContentTypeUpdate {
  slug?: string | null;
  title?: string | null;
  color?: string | null;
  description?: string | null;
  properties?: any | null;
}

export interface CourseContentTypeQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  slug?: string | null;
  title?: string | null;
  color?: string | null;
  description?: string | null;
  course_id?: string | null;
  properties?: string | null;
  course_content_kind_id?: string | null;
}

export interface CourseGroupCreate {
  title?: string | null;
  description?: string | null;
  course_id: string;
  properties?: any | null;
}

export interface CourseGroupGet {
  title?: string | null;
  description?: string | null;
  course_id: string;
  properties?: any | null;
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
}

export interface CourseGroupList {
  id: string;
  title?: string | null;
  course_id: string;
}

export interface CourseGroupUpdate {
  title?: string | null;
  description?: string | null;
  course_id?: string | null;
  properties?: any | null;
}

export interface CourseGroupQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  title?: string | null;
  course_id?: string | null;
  properties?: string | null;
}

export interface GradedByCourseMember {
  course_role_id?: string | null;
  user_id: string;
  user?: GradingAuthor | null;
}

/**
 * Create a new grading for a submission group.
 */
export interface CourseSubmissionGroupGradingCreate {
  course_submission_group_id: string;
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
export interface CourseSubmissionGroupGradingGet {
  created_at: string;
  updated_at: string;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  course_submission_group_id: string;
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
export interface CourseSubmissionGroupGradingList {
  id: string;
  course_submission_group_id: string;
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
export interface CourseSubmissionGroupGradingUpdate {
  grading?: number | null;
  status?: GradingStatus | null;
  feedback?: string | null;
  result_id?: string | null;
}

/**
 * Query parameters for searching gradings.
 */
export interface CourseSubmissionGroupGradingQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  course_submission_group_id?: string | null;
  graded_by_course_member_id?: string | null;
  result_id?: string | null;
  status?: GradingStatus | null;
  min_grade?: number | null;
  max_grade?: number | null;
  has_feedback?: boolean | null;
}

/**
 * Repository information for a submission group
 */
export interface SubmissionGroupRepository {
  provider?: string;
  url: string;
  full_path: string;
  clone_url?: string | null;
  web_url?: string | null;
}

/**
 * Basic member information
 */
export interface SubmissionGroupMemberBasic {
  id: string;
  user_id: string;
  course_member_id: string;
  username?: string | null;
  full_name?: string | null;
}

/**
 * Submission group data for course contents (list view).
 */
export interface SubmissionGroupStudentList {
  id?: string | null;
  course_content_title?: string | null;
  course_content_path?: string | null;
  example_identifier?: string | null;
  max_group_size?: number | null;
  current_group_size?: number;
  members?: SubmissionGroupMemberBasic[];
  repository?: SubmissionGroupRepository | null;
  status?: string | null;
  grading?: number | null;
  count?: number;
  max_submissions?: number | null;
  unread_message_count?: number;
}

/**
 * Detailed submission group view including grading history.
 */
export interface SubmissionGroupStudentGet {
  id?: string | null;
  course_content_title?: string | null;
  course_content_path?: string | null;
  example_identifier?: string | null;
  max_group_size?: number | null;
  current_group_size?: number;
  members?: SubmissionGroupMemberBasic[];
  repository?: SubmissionGroupRepository | null;
  status?: string | null;
  grading?: number | null;
  count?: number;
  max_submissions?: number | null;
  unread_message_count?: number;
  gradings?: CourseSubmissionGroupGradingList[];
}

export interface ResultStudentList {
  execution_backend_id?: string | null;
  test_system_id?: string | null;
  version_identifier?: string | null;
  status?: TaskStatus | null;
  result?: number | null;
  result_json?: any | null;
  submit?: boolean | null;
}

export interface CourseContentStudentProperties {
  gitlab?: GitLabConfigGet | null;
}

export interface CourseContentStudentGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  archived_at?: string | null;
  title?: string | null;
  description?: string | null;
  path: string;
  course_id: string;
  course_content_type_id: string;
  course_content_kind_id: string;
  position: number;
  max_group_size?: number | null;
  submitted?: boolean | null;
  course_content_types: CourseContentTypeGet;
  result_count: number;
  submission_count: number;
  max_test_runs?: number | null;
  unread_message_count?: number;
  result?: ResultStudentList | null;
  directory?: string | null;
  color: string;
  submission_group?: SubmissionGroupStudentGet | null;
}

export interface CourseContentStudentList {
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
  directory?: string | null;
  color: string;
  result?: ResultStudentList | null;
  submission_group?: SubmissionGroupStudentList | null;
  unread_message_count?: number;
}

export interface CourseContentStudentUpdate {
  status?: any | null;
  grading?: number | null;
  feedback?: string | null;
}

export interface CourseContentStudentQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  title?: string | null;
  path?: string | null;
  course_id?: string | null;
  course_content_type_id?: string | null;
  directory?: string | null;
  project?: string | null;
  provider_url?: string | null;
  nlevel?: number | null;
  descendants?: string | null;
  ascendants?: string | null;
}

export interface CourseStudentRepository {
  provider_url?: string | null;
  full_path?: string | null;
}

export interface CourseStudentGet {
  id: string;
  title?: string | null;
  course_family_id?: string | null;
  organization_id?: string | null;
  course_content_types: CourseContentTypeGet[];
  path: string;
  repository: CourseStudentRepository;
}

export interface CourseStudentList {
  id: string;
  title?: string | null;
  course_family_id?: string | null;
  organization_id?: string | null;
  path: string;
  repository: CourseStudentRepository;
}

export interface CourseStudentQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  title?: string | null;
  description?: string | null;
  path?: string | null;
  course_family_id?: string | null;
  organization_id?: string | null;
  provider_url?: string | null;
  full_path?: string | null;
  full_path_student?: string | null;
}

export interface CourseContentKindCreate {
  title?: string | null;
  description?: string | null;
  has_ascendants: boolean;
  has_descendants: boolean;
  submittable: boolean;
}

export interface CourseContentKindGet {
  title?: string | null;
  description?: string | null;
  has_ascendants: boolean;
  has_descendants: boolean;
  submittable: boolean;
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
}

export interface CourseContentKindList {
  id: string;
  title?: string | null;
  has_ascendants: boolean;
  has_descendants: boolean;
  submittable: boolean;
}

export interface CourseContentKindUpdate {
  title?: string | null;
  description?: string | null;
}

export interface CourseContentKindQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  title?: string | null;
  description?: string | null;
  has_ascendants?: boolean | null;
  has_descendants?: boolean | null;
  submittable?: boolean | null;
}

/**
 * DTO for releasing a course.
 */
export interface ReleaseCourseCreate {
  course_id?: string | null;
  gitlab_url?: string | null;
  descendants?: boolean | null;
  deployment?: ComputorDeploymentConfig | null;
}

/**
 * DTO for releasing course content.
 */
export interface ReleaseCourseContentCreate {
  release_dir?: string | null;
  course_id?: string | null;
  gitlab_url?: string | null;
  ascendants?: boolean;
  descendants?: boolean;
  deployment?: ComputorDeploymentConfig | null;
}

/**
 * DTO for updating course release.
 */
export interface CourseReleaseUpdate {
  course?: CourseUpdate | null;
  course_content_types: CourseContentTypeCreate[];
}

/**
 * Request to create a course family via Temporal workflow.
 */
export interface CourseFamilyTaskRequest {
  course_family: Record<string, any>;
  organization_id: string;
  gitlab?: GitLabCredentials | null;
}

/**
 * Request to create a course via Temporal workflow.
 */
export interface CourseTaskRequest {
  course: Record<string, any>;
  course_family_id: string;
  gitlab?: GitLabCredentials | null;
}

/**
 * Configuration for course execution backend.
 */
export interface CourseExecutionBackendConfig {
  /** Unique identifier for the execution backend */
  slug: string;
  /** Version of the execution backend (e.g., 'r2024b', 'v1.0') */
  version: string;
  /** Backend-specific settings */
  settings?: any | null;
}

export interface CourseFamilyProperties {
  gitlab?: GitLabConfig | null;
}

export interface CourseFamilyPropertiesGet {
  gitlab?: GitLabConfigGet | null;
}

export interface CourseFamilyCreate {
  title?: string | null;
  description?: string | null;
  path: string;
  organization_id: string;
  properties?: CourseFamilyProperties | null;
}

export interface CourseFamilyGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  title?: string | null;
  description?: string | null;
  path: string;
  organization_id: string;
  properties?: CourseFamilyPropertiesGet | null;
  organization?: OrganizationGet | null;
}

export interface CourseFamilyList {
  id: string;
  title?: string | null;
  organization_id: string;
  path: string;
}

export interface CourseFamilyUpdate {
  title?: string | null;
  description?: string | null;
  path?: string | null;
  organization_id?: string | null;
  properties?: CourseFamilyProperties | null;
}

export interface CourseFamilyQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  title?: string | null;
  description?: string | null;
  path?: string | null;
  organization_id?: string | null;
  properties?: string | null;
}

/**
 * Properties for course content (stored in JSONB).
 */
export interface CourseContentProperties {
  gitlab?: GitLabConfig | null;
}

/**
 * Properties for course content GET responses.
 */
export interface CourseContentPropertiesGet {
  gitlab?: GitLabConfigGet | null;
}

/**
 * DTO for creating course content.
 */
export interface CourseContentCreate {
  title?: string | null;
  description?: string | null;
  path: string;
  course_id: string;
  course_content_type_id: string;
  properties?: CourseContentProperties | null;
  position?: number;
  max_group_size?: number | null;
  max_test_runs?: number | null;
  max_submissions?: number | null;
  execution_backend_id?: string | null;
}

/**
 * DTO for course content GET responses.
 */
export interface CourseContentGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  archived_at?: string | null;
  title?: string | null;
  description?: string | null;
  path: string;
  course_id: string;
  course_content_type_id: string;
  course_content_kind_id: string;
  properties?: CourseContentPropertiesGet | null;
  position: number;
  max_group_size?: number | null;
  max_test_runs?: number | null;
  max_submissions?: number | null;
  execution_backend_id?: string | null;
  is_submittable?: boolean;
  has_deployment?: boolean | null;
  deployment_status?: string | null;
  /** DEPRECATED: Use deployment API */
  example_version_id?: string | null;
  course_content_type?: CourseContentTypeGet | null;
  /** Deployment information if requested via include=deployment */
  deployment?: CourseContentDeploymentGet | null;
}

/**
 * DTO for course content list responses.
 */
export interface CourseContentList {
  id: string;
  title?: string | null;
  path: string;
  course_id: string;
  course_content_type_id: string;
  course_content_kind_id: string;
  position: number;
  max_group_size?: number | null;
  max_test_runs?: number | null;
  max_submissions?: number | null;
  execution_backend_id?: string | null;
  is_submittable?: boolean;
  course_content_type?: CourseContentTypeList | null;
  /** Whether this content has an example deployment */
  has_deployment?: boolean | null;
  /** Current deployment status if has_deployment=true */
  deployment_status?: string | null;
  /** Deployment information if requested via include=deployment */
  deployment?: CourseContentDeploymentList | null;
}

/**
 * DTO for updating course content.
 */
export interface CourseContentUpdate {
  path?: string | null;
  title?: string | null;
  description?: string | null;
  course_content_type_id?: string | null;
  properties?: CourseContentProperties | null;
  position?: number | null;
  max_group_size?: number | null;
  max_test_runs?: number | null;
  max_submissions?: number | null;
  execution_backend_id?: string | null;
}

/**
 * Query parameters for course content.
 */
export interface CourseContentQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  title?: string | null;
  path?: string | null;
  course_id?: string | null;
  course_content_type_id?: string | null;
  properties?: CourseContentProperties | null;
  archived?: boolean | null;
  position?: number | null;
  max_group_size?: number | null;
  max_test_runs?: number | null;
  max_submissions?: number | null;
  execution_backend_id?: string | null;
  /** Filter by whether content has a deployment */
  has_deployment?: boolean | null;
}

export interface CourseMemberCommentCreate {
  id?: string | null;
  transmitter_id?: string;
  course_member_id: string;
  message: string;
}

export interface CourseMemberCommentGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  transmitter_id?: string;
  transmitter: CourseMemberGet;
  course_member_id: string;
  message: string;
}

export interface CourseMemberCommentList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  transmitter_id?: string;
  transmitter: CourseMemberList;
  course_member_id: string;
  message: string;
}

export interface CourseMemberCommentUpdate {
  message?: string | null;
}

export interface CourseMemberCommentQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  transmitter_id?: string | null;
  course_member_id?: string | null;
}

export interface CourseTutorRepository {
  provider_url?: string | null;
  full_path_reference?: string | null;
}

export interface CourseTutorGet {
  id: string;
  title?: string | null;
  course_family_id?: string | null;
  organization_id?: string | null;
  path: string;
  repository: CourseTutorRepository;
}

export interface CourseTutorList {
  id: string;
  title?: string | null;
  course_family_id?: string | null;
  organization_id?: string | null;
  path: string;
  repository: CourseTutorRepository;
}

export interface CourseTutorQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  title?: string | null;
  description?: string | null;
  path?: string | null;
  course_family_id?: string | null;
  organization_id?: string | null;
}

export interface CourseSignupResponse {
  course_id: string;
  course_title: string;
  role: string;
  repository: string;
}

export interface CourseContentFileQuery {
  filename?: string | null;
}

export interface CommentCreate {
  course_member_id: any;
  message: string;
}

export interface CommentUpdate {
  message: string;
}