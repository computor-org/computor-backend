/**
 * Workspace types for the web UI.
 *
 * The backend DTOs (computor_types/{coder,course_workspaces,workspace_roles}.py)
 * are generated into types/generated and re-exported here so existing import
 * sites keep working. This file only adds what codegen cannot express:
 *
 * - runtime constants (codegen emits no values),
 * - narrowings of fields that are plain `str`/dict in pydantic,
 * - re-required response fields that codegen marks optional because the
 *   pydantic field has a default, although the server always serializes them.
 *
 * Narrowings are built ON TOP of the generated type (`Gen & {...}`), never
 * free-standing mirrors, so any other field change flows in automatically.
 * See src/types/README.md for the convention.
 */

import type {
  WorkspaceCredentialOutcome,
  WorkspaceCredentialRotationResponse as GenWorkspaceCredentialRotationResponse,
  CoderTemplateFleetStatus as GenCoderTemplateFleetStatus,
  CoderFleetStatusResponse as GenCoderFleetStatusResponse,
  CourseStudentWorkspaceEntry as GenCourseStudentWorkspaceEntry,
  CourseStudentWorkspacesResponse as GenCourseStudentWorkspacesResponse,
  CourseWorkspaceAdminItem as GenCourseWorkspaceAdminItem,
  CourseWorkspaceAdminListResponse as GenCourseWorkspaceAdminListResponse,
  CourseWorkspaceSettingsGet as GenCourseWorkspaceSettingsGet,
  CourseWorkspaceTemplateItem as GenCourseWorkspaceTemplateItem,
  CoderTemplate,
  CoderWorkspace,
  StudentWorkspaceProvisionOutcome,
  StudentWorkspaceProvisionResponse as GenStudentWorkspaceProvisionResponse,
  TemplateCatalogEntry as GenTemplateCatalogEntry,
  TemplateCatalogResponse as GenTemplateCatalogResponse,
  TemplateListResponse as GenTemplateListResponse,
  TemplateMetadata as GenTemplateMetadata,
  TemplateMetadataUpdateResponse as GenTemplateMetadataUpdateResponse,
  TemplatePreparation as GenTemplatePreparation,
  TemplateSettingsListResponse as GenTemplateSettingsListResponse,
  WorkspaceListResponse as GenWorkspaceListResponse,
  WorkspaceRoleUser as GenWorkspaceRoleUser,
  WorkspaceTemplateSettingsSchema,
} from 'types/generated';

// --- Backend DTOs re-exported unchanged from the generated types ---

export type {
  CoderUser,
  CoderWorkspace,
  WorkspaceDetails,
  WorkspaceStatus,
  WorkspaceBuildStatus,
  ProvisionResult,
  CoderTemplate,
  WorkspaceActionResponse,
  CoderHealthResponse,
  WorkspaceRoleAssign,
  WorkspaceProvisionRequest,
  ImageBuildRequest,
  TemplatePushRequest,
  WorkspaceRolloutRequest,
  CoderAdminTaskResponse,
  WorkspaceTemplateSettingsUpdate,
  TemplateFile,
  TemplateFilesResponse,
  TemplateFileActionResponse,
  TemplateVariable,
  TemplateVariablesResponse,
  TemplateMetadataUpdate,
  TemplateCloneRequest,
  TemplateDeleteResponse,
  WorkspaceVolume,
  WorkspaceVolumeListResponse,
  CourseWorkspaceTemplatePolicy,
  CourseWorkspaceSettingsUpdate,
  StudentWorkspaceProvisionRequest,
  StudentWorkspaceProvisionOutcome,
  WorkspaceCredentialOutcome,
} from 'types/generated';

// Pydantic names it WorkspaceTemplateSettingsSchema; the UI keeps the short
// name and re-requires the always-serialized fields.
export type WorkspaceTemplateSettings = WorkspaceTemplateSettingsSchema & {
  enabled: boolean;
  allow_root: boolean;
  allow_internet: boolean;
  template_variables: Record<string, string>;
};

// A template's manifest-backed identity/display metadata; the server always
// serializes the flags codegen marks optional.
export type TemplateMetadata = GenTemplateMetadata & { customized: boolean };
export type TemplateMetadataUpdateResponse = GenTemplateMetadataUpdateResponse & {
  customized: boolean;
  coder_updated: boolean;
};

// --- UI-only: agent lifecycle ---

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

// --- UI-only narrowings of untyped pydantic fields ---

/** Narrows CoderTemplateFleetStatus.rollout_state (a plain string in pydantic). */
export type TemplateRolloutState =
  | 'unavailable'
  | 'building'
  | 'ready'
  | 'rolling_out'
  | 'scheduled_on_start'
  | 'up_to_date';

/** Per-template entry of CoderTaskProgress.templates (untyped dict in pydantic). */
export interface CoderTemplateTaskProgress {
  key: string;
  name: string;
  display_name?: string | null;
  status: 'pending' | 'running' | 'succeeded' | 'failed';
  phase: string;
  error?: string | null;
  result?: Record<string, unknown> | null;
  /**
   * Commit each tracked source repo was built from, keyed by its build arg
   * (e.g. `EXTENSION_REPO_SHA`). Absent on older backends and on pushes that
   * did not build.
   */
  source_revisions?: Record<string, string> | null;
}

/** Shape of TaskInfo.progress for coder admin tasks (untyped dict in pydantic). */
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

/**
 * Value-bearing mirror of the generated TaskStatus union: components compare
 * and construct statuses (TaskStatus.QUEUED, …), which a type-only union
 * cannot provide. Enum members are assignable to the generated union.
 */
export enum TaskStatus {
  QUEUED = 'queued',
  STARTED = 'started',
  FINISHED = 'finished',
  FAILED = 'failed',
  DEFERRED = 'deferred',
  CANCELLED = 'cancelled',
}

/** Narrows the generated TaskInfo: progress is typed for coder admin tasks. */
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

/** Narrows the generated CoderAdminTaskListResponse to the typed TaskInfo. */
export interface CoderAdminTaskListResponse {
  tasks: TaskInfo[];
}

// --- Response types with server-guaranteed fields re-required ---
// (Optional in the generated type only because the pydantic field has a
// default; the endpoints always serialize them.)

export type WorkspaceListResponse = GenWorkspaceListResponse & {
  workspaces: CoderWorkspace[];
  count: number;
};

export type WorkspaceRoleUser = GenWorkspaceRoleUser & {
  roles: string[];
};

export type TemplatePreparation = GenTemplatePreparation & {
  status: 'pending' | 'running' | 'succeeded' | 'failed';
  phase: string;
  deployed: boolean;
};

export type TemplateListResponse = Omit<GenTemplateListResponse, 'templates' | 'preparing'> & {
  templates: CoderTemplate[];
  /** Scoped exactly like `templates`; absent on older backends. */
  preparing?: TemplatePreparation[];
};

export type TemplateCatalogEntry = GenTemplateCatalogEntry & {
  deployed: boolean;
  enabled: boolean;
  customized: boolean;
  workspace_count: number;
  running_workspace_count: number;
};

export type TemplateCatalogResponse = Omit<GenTemplateCatalogResponse, 'templates'> & {
  templates: TemplateCatalogEntry[];
  templates_dir_available: boolean;
};

export type TemplateSettingsListResponse = Omit<GenTemplateSettingsListResponse, 'settings'> & {
  settings: WorkspaceTemplateSettings[];
};

export type CoderTemplateFleetStatus = Omit<GenCoderTemplateFleetStatus, 'rollout_state'> & {
  rollout_state: TemplateRolloutState;
  workspace_count: number;
  current_count: number;
  outdated_count: number;
  running_outdated_count: number;
  scheduled_on_start_count: number;
  actionable_count: number;
};

export type CoderFleetStatusResponse = Omit<GenCoderFleetStatusResponse, 'templates'> & {
  templates: CoderTemplateFleetStatus[];
  healthy: boolean;
  workspace_count: number;
};

export type CourseWorkspaceTemplateItem = GenCourseWorkspaceTemplateItem & {
  enabled: boolean;
  template_allow_root: boolean;
  template_allow_internet: boolean;
  effective_allow_root: boolean;
  effective_allow_internet: boolean;
};

export type CourseWorkspaceSettingsGet = Omit<GenCourseWorkspaceSettingsGet, 'templates'> & {
  templates: CourseWorkspaceTemplateItem[];
  lecturer_provision_enabled: boolean;
  can_manage: boolean;
};

export type CourseWorkspaceAdminItem = GenCourseWorkspaceAdminItem & {
  template_names: string[];
  lecturer_provision_enabled: boolean;
};

export type CourseWorkspaceAdminListResponse = Omit<GenCourseWorkspaceAdminListResponse, 'courses'> & {
  courses: CourseWorkspaceAdminItem[];
};

export type StudentWorkspaceProvisionResponse = GenStudentWorkspaceProvisionResponse & {
  outcomes: StudentWorkspaceProvisionOutcome[];
  succeeded: number;
  failed: number;
};

export type CourseStudentWorkspaceEntry = GenCourseStudentWorkspaceEntry & {
  workspaces: CoderWorkspace[];
};

export type CourseStudentWorkspacesResponse = Omit<GenCourseStudentWorkspacesResponse, 'students'> & {
  students: CourseStudentWorkspaceEntry[];
  count: number;
};

export type WorkspaceCredentialRotationResponse = GenWorkspaceCredentialRotationResponse & {
  key_version: number;
  pushed: boolean;
  outcomes: WorkspaceCredentialOutcome[];
  succeeded: number;
  failed: number;
};
