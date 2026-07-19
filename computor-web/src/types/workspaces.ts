/**
 * TypeScript interfaces for Coder workspace management.
 *
 * Mirrors the Python Pydantic schemas from:
 * - computor-backend/src/computor_backend/coder/schemas.py
 * - computor-types/src/computor_types/workspace_roles.py
 */

// --- Enums ---

export enum WorkspaceStatus {
  PENDING = 'pending',
  STARTING = 'starting',
  RUNNING = 'running',
  STOPPING = 'stopping',
  STOPPED = 'stopped',
  FAILED = 'failed',
  CANCELING = 'canceling',
  CANCELED = 'canceled',
  DELETING = 'deleting',
  DELETED = 'deleted',
}

export enum WorkspaceBuildStatus {
  PENDING = 'pending',
  STARTING = 'starting',
  RUNNING = 'running',
  STOPPING = 'stopping',
  STOPPED = 'stopped',
  SUCCEEDED = 'succeeded',
  FAILED = 'failed',
  CANCELING = 'canceling',
  CANCELED = 'canceled',
  DELETING = 'deleting',
}

// --- Coder Response Types ---

export interface CoderUser {
  id: string;
  username: string;
  email: string;
  name?: string | null;
  created_at?: string | null;
  status?: string | null;
}

export interface CoderWorkspace {
  id: string;
  name: string;
  owner_id: string;
  owner_name?: string | null;
  template_id: string;
  /** Raw template name (stable identifier, e.g. 'python-workspace'). */
  template_name?: string | null;
  /** Human-readable template display name; fall back to template_name. */
  template_display_name?: string | null;
  template_version_id?: string | null;
  template_version_name?: string | null;
  latest_build_transition?: string | null;
  latest_build_status?: WorkspaceBuildStatus | null;
  latest_build_id?: string | null;
  /**
   * Home volume mode ('shared' | 'scratch') from the latest build's rich
   * parameters; only populated by views that need it (lecturer console).
   */
  home_mode?: string | null;
  automatic_updates?: 'always' | 'never' | null;
  created_at?: string | null;
  updated_at?: string | null;
}

/** Coder agent lifecycle_state — how far the agent's startup script got. */
export type AgentLifecycle =
  | 'created'
  | 'starting'
  | 'ready'
  | 'start_timeout'
  | 'start_error'
  | 'off'
  | 'shutting_down'
  | 'shutdown_timeout'
  | 'shutdown_error';

/** Lifecycle states that mean the startup script will never report ready. */
export const AGENT_LIFECYCLE_GAVE_UP: readonly string[] = ['start_timeout', 'start_error'];

export interface WorkspaceDetails {
  workspace: CoderWorkspace;
  status: WorkspaceStatus;
  access_url?: string | null;
  code_server_url?: string | null;
  health?: string | boolean | null;
  resources?: Record<string, unknown> | null;
  /** How far the agent's startup script got; absent on older backends. */
  agent_lifecycle?: AgentLifecycle | string | null;
  /**
   * Running AND the agent finished its startup script. `status === 'running'`
   * alone only means the Terraform apply succeeded — the service inside may
   * still be booting — so prefer this before sending a user to the URL.
   */
  ready?: boolean;
}

export interface ProvisionResult {
  user: CoderUser;
  workspace?: CoderWorkspace | null;
  created_user: boolean;
  created_workspace: boolean;
  code_server_password?: string | null;
}

export interface CoderTemplate {
  id: string;
  name: string;
  display_name?: string | null;
  description?: string | null;
  icon?: string | null;
  active_version_id?: string | null;
  created_at?: string | null;
}

export interface WorkspaceListResponse {
  workspaces: CoderWorkspace[];
  count: number;
}

export interface TemplateListResponse {
  templates: CoderTemplate[];
  count: number;
}

export interface WorkspaceActionResponse {
  success: boolean;
  message: string;
  workspace_id?: string | null;
  new_status?: WorkspaceStatus | null;
}

export interface CoderHealthResponse {
  healthy: boolean;
  version?: string | null;
  message?: string | null;
}

// --- Workspace Roles Types ---

export interface WorkspaceRoleUser {
  user_id: string;
  email: string | null;
  username: string | null;
  given_name: string | null;
  family_name: string | null;
  roles: string[];
}

// Identical to the backend schema, so re-export the generated type rather
// than re-declaring it — this one can't drift (TASK-412). The other coder
// schemas below still lack generated equivalents (their endpoints aren't in
// the client/type codegen yet); WorkspaceProvisionRequest is kept hand-written
// on purpose — it accepts a permissive `template?: string | null` rather than
// the generated WorkspaceTemplate union.
export type { WorkspaceRoleAssign } from 'types/generated';

export interface WorkspaceProvisionRequest {
  email?: string | null;
  /** Raw template name; omit for the server default. */
  template?: string | null;
  /** Custom workspace name; omit for a name derived from the template. */
  workspace_name?: string | null;
  /**
   * Home volume mode; full provisioners only. Self-provisioning always uses
   * the template default (shared).
   */
  home_mode?: 'shared' | 'scratch' | null;
}

// --- Admin: image build / template push / fleet rollout ---

export interface ImageBuildRequest {
  templates?: string[] | null;
  image_tag?: string | null;
}

export interface TemplatePushRequest {
  templates?: string[] | null;
  build_images?: boolean;
  image_tag?: string | null;
}

export interface WorkspaceRolloutRequest {
  templates?: string[] | null;
}

export interface CoderAdminTaskResponse {
  workflow_id: string;
  task_name: string;
  status: string;
}

export type TemplateRolloutState =
  | 'unavailable'
  | 'building'
  | 'ready'
  | 'rolling_out'
  | 'scheduled_on_start'
  | 'up_to_date';

export interface CoderTemplateFleetStatus {
  id: string;
  name: string;
  display_name?: string | null;
  active_version_id?: string | null;
  workspace_count: number;
  current_count: number;
  outdated_count: number;
  running_outdated_count: number;
  scheduled_on_start_count: number;
  actionable_count: number;
  rollout_state: TemplateRolloutState;
}

export interface CoderFleetStatusResponse {
  healthy: boolean;
  version?: string | null;
  templates: CoderTemplateFleetStatus[];
  workspace_count: number;
}

export interface CoderTemplateTaskProgress {
  key: string;
  name: string;
  display_name?: string | null;
  status: 'pending' | 'running' | 'succeeded' | 'failed';
  phase: string;
  error?: string | null;
  result?: Record<string, unknown> | null;
}

export interface CoderTaskProgress {
  phase?: string;
  operation_status?: string;
  image_tag?: string;
  current_template?: string | null;
  completed?: number;
  total?: number;
  templates?: CoderTemplateTaskProgress[];
  result?: Record<string, unknown> | null;
}

export interface CoderAdminTaskListResponse {
  tasks: TaskInfo[];
}

// --- Admin: per-template settings (resource limits, seat quota) + editing ---

export interface WorkspaceTemplateSettings {
  /** Coder template name (e.g. 'vscode-workspace'). */
  template_name: string;
  /**
   * Disabled templates are hidden from non-manager listings and cannot be
   * provisioned by non-managers; existing workspaces keep running.
   */
  enabled: boolean;
  /** Container memory cap in MiB applied at push time; null/0 = unlimited. */
  memory_mb?: number | null;
  /** Relative CPU weight applied at push time; null/0 = Docker default. */
  cpu_shares?: number | null;
  /** Max concurrently running workspaces across all users; null = unlimited. */
  max_running_workspaces?: number | null;
  /** Extra Terraform variable overrides pushed as --variable. */
  template_variables: Record<string, string>;
  updated_at?: string | null;
}

export interface WorkspaceTemplateSettingsUpdate {
  enabled?: boolean;
  memory_mb?: number | null;
  cpu_shares?: number | null;
  max_running_workspaces?: number | null;
  template_variables?: Record<string, string>;
}

export interface TemplateSettingsListResponse {
  settings: WorkspaceTemplateSettings[];
}

export interface TemplateFile {
  name: string;
  content: string;
}

export interface TemplateFilesResponse {
  template_name: string;
  dir_name: string;
  /**
   * True when the deployed template is operator-customized (the
   * .computor-managed marker is gone) and no longer auto-synced from the repo.
   */
  customized: boolean;
  files: TemplateFile[];
}

export interface TemplateFileActionResponse {
  success: boolean;
  message: string;
  customized: boolean;
}

export interface TemplateVariable {
  name: string;
  type?: string | null;
  /** Declared default; masked (null) for sensitive variables. */
  default?: unknown;
  has_default: boolean;
  description?: string | null;
  sensitive: boolean;
  /** Owned by the deployment (push pipeline / env / infra wiring) — not overridable. */
  managed: boolean;
  managed_reason?: string | null;
  /** The .tf file declaring this variable. */
  file: string;
}

export interface TemplateVariablesResponse {
  template_name: string;
  dir_name: string;
  customized: boolean;
  variables: TemplateVariable[];
}

// --- Course-scoped workspaces (computor_types/course_workspaces.py) ---

export interface CourseWorkspaceTemplateItem {
  template_name: string;
  /** Global enable state (a template without a settings row is enabled). */
  enabled: boolean;
  display_name?: string | null;
  description?: string | null;
  icon?: string | null;
  /** Whether Coder currently has this template; null when Coder was unreachable. */
  exists_in_coder?: boolean | null;
}

export interface CourseWorkspaceSettingsGet {
  course_id: string;
  templates: CourseWorkspaceTemplateItem[];
  /** Whether course lecturers may bulk-provision workspaces for students. */
  lecturer_provision_enabled: boolean;
  /** Managers only: globally enabled Coder templates to pick from. */
  available?: CoderTemplate[] | null;
  can_manage: boolean;
}

export interface CourseWorkspaceSettingsUpdate {
  /** Allowed Coder template names (full replacement). */
  template_names: string[];
  lecturer_provision_enabled?: boolean;
}

export interface CourseWorkspaceAdminItem {
  course_id: string;
  title?: string | null;
  path?: string | null;
  template_names: string[];
  lecturer_provision_enabled: boolean;
}

export interface CourseWorkspaceAdminListResponse {
  courses: CourseWorkspaceAdminItem[];
}

export interface StudentWorkspaceProvisionRequest {
  /** Course-allowed Coder template name. */
  template_name: string;
  course_member_ids: string[];
  /** 'scratch' = throwaway per-workspace home (deleted with the workspace). */
  home_mode?: 'shared' | 'scratch';
  /** Optional name suffix (e.g. 'exam1'); defaults to 'tmp'. */
  label?: string | null;
}

export interface StudentWorkspaceProvisionOutcome {
  course_member_id: string;
  user_id?: string | null;
  full_name?: string | null;
  workspace_name?: string | null;
  success: boolean;
  error?: string | null;
}

export interface StudentWorkspaceProvisionResponse {
  outcomes: StudentWorkspaceProvisionOutcome[];
  succeeded: number;
  failed: number;
}

export interface CourseStudentWorkspaceEntry {
  course_member_id: string;
  user_id: string;
  full_name?: string | null;
  workspaces: CoderWorkspace[];
}

export interface CourseStudentWorkspacesResponse {
  students: CourseStudentWorkspaceEntry[];
  count: number;
}

export enum TaskStatus {
  QUEUED = 'queued',
  STARTED = 'started',
  FINISHED = 'finished',
  FAILED = 'failed',
  DEFERRED = 'deferred',
  CANCELLED = 'cancelled',
}

export interface TaskInfo {
  task_id: string;
  task_name: string;
  status: TaskStatus;
  error?: string | null;
  progress?: CoderTaskProgress | null;
  created_at?: string;
  started_at?: string | null;
  finished_at?: string | null;
  workflow_id?: string | null;
  duration?: string | null;
}
