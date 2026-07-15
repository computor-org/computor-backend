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
  automatic_updates?: 'always' | 'never' | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface WorkspaceDetails {
  workspace: CoderWorkspace;
  status: WorkspaceStatus;
  access_url?: string | null;
  code_server_url?: string | null;
  health?: string | boolean | null;
  resources?: Record<string, unknown> | null;
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
