/**
 * TypeScript interfaces for Coder workspace management.
 *
 * Mirrors the Python Pydantic schemas from:
 * - computor-backend/src/computor_backend/coder/schemas.py
 * - computor-types/src/computor_types/workspace_roles.py
 */

// --- Enums ---

export enum WorkspaceTemplate {
  PYTHON = 'python-workspace',
  MATLAB = 'matlab-workspace',
}

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
  template_name?: string | null;
  latest_build_status?: WorkspaceBuildStatus | null;
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

export interface WorkspaceRoleAssign {
  email: string;
  role_id: string;
}

export interface WorkspaceProvisionRequest {
  email?: string | null;
  template?: WorkspaceTemplate;
  workspace_name?: string | null;
}
