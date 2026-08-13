/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Workspaces

 */



import type { TaskInfo } from './tasks';



/**
 * Course-level narrowing of a template's root/internet policy.
 * 
 * ``None`` means "inherit the template" — a course can only ever take access
 * away, so setting True on something the template denies changes nothing.
 */
export interface CourseWorkspaceTemplatePolicy {
  /** False denies sudo/su for this course; None inherits the template */
  allow_root?: boolean | null;
  /** False denies internet for this course; None inherits the template */
  allow_internet?: boolean | null;
}

/**
 * One template allowed in a course, enriched from Coder best-effort.
 */
export interface CourseWorkspaceTemplateItem {
  /** Coder template name (e.g. 'vscode-workspace') */
  template_name: string;
  /** Global enable state (a template without a settings row is enabled) */
  enabled?: boolean;
  /** Coder display name (None when Coder unreachable) */
  display_name?: string | null;
  /** Coder template description */
  description?: string | null;
  /** Coder template icon URL/path */
  icon?: string | null;
  /** Whether Coder currently has this template; None when Coder was unreachable */
  exists_in_coder?: boolean | null;
  /** This course's root policy; None = inherit the template */
  allow_root?: boolean | null;
  /** This course's internet policy; None = inherit the template */
  allow_internet?: boolean | null;
  /** The template's ceiling — a course cannot grant beyond it */
  template_allow_root?: boolean;
  /** The template's internet ceiling */
  template_allow_internet?: boolean;
  /** What a workspace provisioned for this course actually gets */
  effective_allow_root?: boolean;
  /** What a workspace provisioned for this course actually gets */
  effective_allow_internet?: boolean;
}

/**
 * A course's workspace configuration.
 * 
 * Non-managers only see globally enabled templates; ``available`` (the
 * picker source for the admin UI) is present for managers only.
 */
export interface CourseWorkspaceSettingsGet {
  course_id: string;
  templates?: CourseWorkspaceTemplateItem[];
  /** Whether course lecturers may bulk-provision workspaces for students */
  lecturer_provision_enabled?: boolean;
  /** Managers only: globally enabled Coder templates to pick from */
  available?: CoderTemplate[] | null;
  /** Whether the caller may PUT this configuration */
  can_manage?: boolean;
}

/**
 * Replace-list payload for a course's workspace configuration (workspace:manage).
 */
export interface CourseWorkspaceSettingsUpdate {
  /** Allowed Coder template names (full replacement) */
  template_names?: string[];
  lecturer_provision_enabled?: boolean;
  /** Per-template root/internet narrowing, keyed by template name. Templates absent from this map inherit their template's policy; keys not present in template_names are ignored. */
  template_policies?: Record<string, CourseWorkspaceTemplatePolicy>;
}

/**
 * One course row in the workspace-admin Courses view.
 */
export interface CourseWorkspaceAdminItem {
  course_id: string;
  title?: string | null;
  path?: string | null;
  template_names?: string[];
  lecturer_provision_enabled?: boolean;
}

/**
 * All courses with their workspace configuration (workspace:manage).
 */
export interface CourseWorkspaceAdminListResponse {
  courses?: CourseWorkspaceAdminItem[];
}

/**
 * Lecturer request to provision workspaces for selected course members.
 */
export interface StudentWorkspaceProvisionRequest {
  /** Course-allowed Coder template name */
  template_name: string;
  /** Course members to provision for */
  course_member_ids: string[];
  /** 'scratch' = throwaway per-workspace home volume (deleted with the workspace); 'shared' = the student's usual home volume */
  home_mode?: "shared" | "scratch";
  /** Optional name suffix (e.g. 'exam1') so the workspace name cannot collide with the student's self-provisioned one; defaults to 'tmp' */
  label?: string | null;
}

/**
 * Per-student result of a bulk provisioning run.
 */
export interface StudentWorkspaceProvisionOutcome {
  course_member_id: string;
  user_id?: string | null;
  full_name?: string | null;
  workspace_name?: string | null;
  success?: boolean;
  /** Failure reason; None on success */
  error?: string | null;
}

/**
 * Bulk provisioning outcomes (the batch never aborts on a single failure).
 */
export interface StudentWorkspaceProvisionResponse {
  outcomes?: StudentWorkspaceProvisionOutcome[];
  succeeded?: number;
  failed?: number;
}

/**
 * A course member together with their course-relevant workspaces.
 */
export interface CourseStudentWorkspaceEntry {
  course_member_id: string;
  user_id: string;
  full_name?: string | null;
  workspaces?: CoderWorkspace[];
}

/**
 * Lecturer view: workspaces of course members using course-allowed templates.
 */
export interface CourseStudentWorkspacesResponse {
  students?: CourseStudentWorkspaceEntry[];
  count?: number;
}

/**
 * Schema for creating a Coder user.
 */
export interface CoderUserCreate {
  /** Unique username */
  username: string;
  /** User email address */
  email: string;
  /** User password */
  password: string;
  /** Display name */
  full_name?: string | null;
}

/**
 * Schema for creating a Coder workspace.
 */
export interface CoderWorkspaceCreate {
  /** Workspace name */
  name: string;
  /** Workspace template name (must exist in Coder) */
  template: string;
  /** Per-user credential the workspace app requires and the workspace ingress injects, so one workspace cannot drive another directly. None leaves the app unauthenticated. */
  app_secret?: string | null;
  /** Argon2id hash of app_secret, used by the code-server templates as HASHED_PASSWORD and as the injected session cookie. */
  app_password_hash?: string | null;
  /** Pre-minted API token for automatic extension authentication */
  computor_auth_token?: string | null;
  /** Home volume mode: 'shared' (per-user home volume) or 'scratch' (throwaway per-workspace volume). None = template default (shared). */
  home_mode?: string | null;
  /** Course-level root policy for this workspace. The template ANDs it with its own allow_root, so False always denies but True only permits what the template already allows. None = no course-level restriction. */
  allow_root?: boolean | null;
  /** Course-level internet policy for this workspace, ANDed with the template's allow_internet the same way. None = no course-level restriction. */
  allow_internet?: boolean | null;
  /** Course this workspace is provisioned FOR. None/empty means the user provisioned it for themselves, which is what course views scope on: without it, a member's personal workspace on a course template is indistinguishable from one the course created. */
  course_id?: string | null;
}

/**
 * Coder user information.
 */
export interface CoderUser {
  /** Coder user ID (UUID) */
  id: string;
  /** Username */
  username: string;
  /** Email address */
  email: string;
  /** Display name */
  name?: string | null;
  /** Creation timestamp */
  created_at?: string | null;
  /** User status */
  status?: string | null;
}

/**
 * Coder workspace information.
 */
export interface CoderWorkspace {
  /** Workspace ID (UUID) */
  id: string;
  /** Workspace name */
  name: string;
  /** Owner user ID */
  owner_id: string;
  /** Owner username */
  owner_name?: string | null;
  /** Computor user id decoded from owner_name (see coder/naming.py). None for owners we did not create — Coder's own 'admin' account. Only populated by views that resolve owners. */
  owner_user_id?: string | null;
  /** Full name of the Computor user behind owner_name; only populated by views that resolve owners, and None when the user has no name set */
  owner_display_name?: string | null;
  /** Email of the Computor user behind owner_name; only populated by views that resolve owners */
  owner_email?: string | null;
  /** Template ID */
  template_id: string;
  /** Raw template name (stable identifier, e.g. 'python-workspace') */
  template_name?: string | null;
  /** Human-readable template display name */
  template_display_name?: string | null;
  /** Template version the latest build ran (for fleet/update views) */
  template_version_id?: string | null;
  /** Human-readable template version name of the latest build */
  template_version_name?: string | null;
  /** Transition of the latest build: start | stop | delete */
  latest_build_transition?: string | null;
  /** Latest build status */
  latest_build_status?: WorkspaceBuildStatus | null;
  /** ID of the latest build (for reading its rich parameters) */
  latest_build_id?: string | null;
  /** Home volume mode ('shared' | 'scratch') read from the latest build's rich parameters; only populated by views that need it */
  home_mode?: string | null;
  /** Coder automatic update policy: always | never */
  automatic_updates?: string | null;
  /** Creation timestamp */
  created_at?: string | null;
  /** Last update timestamp */
  updated_at?: string | null;
}

/**
 * Detailed workspace information including access URLs.
 */
export interface WorkspaceDetails {
  /** Workspace info */
  workspace: CoderWorkspace;
  /** Current workspace status */
  status: WorkspaceStatus;
  /** Direct workspace access URL */
  access_url?: string | null;
  /** Code-server URL */
  code_server_url?: string | null;
  /** Workspace health status */
  health?: (string | boolean) | null;
  /** Workspace resources */
  resources?: Record<string, unknown> | null;
  /** Coder agent lifecycle_state: created|starting|ready|start_timeout|start_error|off|shutting_down|shutdown_*. Reports how far the agent's startup script got, unlike the connection status in `resources`. */
  agent_lifecycle?: string | null;
  /** Workspace is RUNNING and its agent finished its startup script. RUNNING alone only means the Terraform apply succeeded, so the service inside may still be booting; prefer this before sending a user to the URL. */
  ready?: boolean;
}

/**
 * Result of user/workspace provisioning.
 */
export interface ProvisionResult {
  /** Created or existing Coder user */
  user: CoderUser;
  /** Created workspace */
  workspace?: CoderWorkspace | null;
  /** Whether user was newly created */
  created_user?: boolean;
  /** Whether workspace was newly created */
  created_workspace?: boolean;
}

/**
 * Coder template information.
 */
export interface CoderTemplate {
  /** Template ID */
  id: string;
  /** Template name */
  name: string;
  /** Display name */
  display_name?: string | null;
  /** Template description */
  description?: string | null;
  /** Template icon URL */
  icon?: string | null;
  /** Active version ID */
  active_version_id?: string | null;
  /** Creation timestamp */
  created_at?: string | null;
}

/**
 * Response for listing workspaces.
 */
export interface WorkspaceListResponse {
  workspaces?: CoderWorkspace[];
  /** Total count */
  count?: number;
}

/**
 * A template an administrator is deploying right now, and how far it got.
 * 
 * Nothing is deployed automatically, so between an admin picking a template
 * and users being able to pick it lies an image build and a push — tens of
 * minutes for something like MATLAB. Coder has no such template yet, so it
 * cannot appear in a template listing, and a user is left staring at a
 * choice that silently lacks the one they were told to use.
 * 
 * ``status``/``phase`` are the workflow's own pair (see
 * tasks/temporal_coder_setup.py), passed through untranslated so the web
 * renders them with the same stage vocabulary the administration page uses.
 */
export interface TemplatePreparation {
  /** Coder template name (e.g. 'vscode-workspace') */
  name: string;
  /** Human-readable name */
  display_name?: string | null;
  /** What the template offers */
  description?: string | null;
  /** Coder icon path or absolute URL */
  icon?: string | null;
  /** Per-template workflow status: pending | running | succeeded | failed */
  status: string;
  /** Per-template phase: queued | building | pushing | rolling_out | complete */
  phase: string;
  /** Coder already has this template, so this run is an update and the current version stays usable while it runs */
  deployed?: boolean;
  /** Workflow behind it: build_workspace_images | push_coder_templates | rollout_workspaces */
  task_name: string;
}

/**
 * Response for listing templates.
 */
export interface TemplateListResponse {
  templates?: CoderTemplate[];
  /** Total count */
  count?: number;
  /** Templates being deployed right now, with the stage each has reached. Scoped exactly like `templates` — a user only ever sees the ones they would be allowed to pick. */
  preparing?: TemplatePreparation[];
}

/**
 * Response for workspace actions (start/stop/delete).
 */
export interface WorkspaceActionResponse {
  /** Whether action was successful */
  success: boolean;
  /** Status message */
  message: string;
  /** Workspace ID */
  workspace_id?: string | null;
  /** New workspace status */
  new_status?: WorkspaceStatus | null;
}

/**
 * Coder server health check response.
 */
export interface CoderHealthResponse {
  /** Whether Coder is healthy */
  healthy: boolean;
  /** Coder version */
  version?: string | null;
  /** Status message */
  message?: string | null;
}

/**
 * Request to login to Coder.
 */
export interface CoderLoginRequest {
  password: string;
  redirect_url?: string | null;
}

/**
 * Response with Coder session token.
 */
export interface CoderSessionResponse {
  success: boolean;
  session_token?: string | null;
  message: string;
}

/**
 * Request to build workspace Docker images.
 */
export interface ImageBuildRequest {
  /** Template names to build (e.g. ['python3.13', 'matlab']). None = all templates. */
  templates?: string[] | null;
  /** Immutable image tag to publish alongside :latest (e.g. 'v20260706-1400'). None = auto-generated from the run time. */
  image_tag?: string | null;
}

/**
 * Request to push Coder templates (Terraform configs).
 */
export interface TemplatePushRequest {
  /** Template names to push (e.g. ['python-workspace', 'matlab-workspace']). None = all templates. */
  templates?: string[] | null;
  /** Build workspace images before pushing templates. */
  build_images?: boolean;
  /** Immutable image tag the pushed template version pins to (and builds, when build_images). None = auto-generated from the run time. */
  image_tag?: string | null;
  /** Rebuild every image layer from scratch. Templates that build from an external repo already re-run that checkout whenever the repo moves, so this is only for cache staleness that mechanism does not cover — it is much slower. */
  no_cache?: boolean;
}

/**
 * Request to roll existing workspaces onto their template's active version.
 */
export interface WorkspaceRolloutRequest {
  /** Template names to roll out (e.g. ['python3.13']). None = all templates. */
  templates?: string[] | null;
}

/**
 * Response for admin task submission.
 */
export interface CoderAdminTaskResponse {
  /** Temporal workflow ID for tracking */
  workflow_id: string;
  /** Name of the submitted task */
  task_name: string;
  /** Initial task status */
  status?: string;
}

/**
 * Update readiness for one Coder template.
 */
export interface CoderTemplateFleetStatus {
  id: string;
  name: string;
  display_name?: string | null;
  active_version_id?: string | null;
  workspace_count?: number;
  current_count?: number;
  outdated_count?: number;
  running_outdated_count?: number;
  scheduled_on_start_count?: number;
  actionable_count?: number;
  rollout_state: string;
}

/**
 * Privileged template-centric fleet summary.
 */
export interface CoderFleetStatusResponse {
  healthy: boolean;
  version?: string | null;
  templates?: CoderTemplateFleetStatus[];
  workspace_count?: number;
}

/**
 * Recent Coder image/template administration workflows.
 */
export interface CoderAdminTaskListResponse {
  tasks?: TaskInfo[];
}

/**
 * One workspace template as it exists on disk, plus its live state.
 * 
 * The catalog is the union of the template directories shipped with the
 * deployment and the templates Coder actually has. A directory that was
 * never pushed still appears here (``deployed=False``) — that is the whole
 * point: an admin has to be able to see and deploy a template the first
 * startup deliberately skipped.
 */
export interface TemplateCatalogEntry {
  /** Template directory name (e.g. 'vscode'); null for a template that is live in Coder but has no directory here (pushed by hand, or its directory was removed) — such a template cannot be rebuilt from this deployment. */
  dir_name?: string | null;
  /** Coder template name (e.g. 'vscode-workspace') */
  name: string;
  /** Human-readable name */
  display_name?: string | null;
  /** What the template offers */
  description?: string | null;
  /** Coder icon path or absolute URL */
  icon?: string | null;
  /** Docker image the template builds */
  image_name?: string | null;
  /** Whether Coder currently has this template */
  deployed?: boolean;
  /** Coder template ID when deployed */
  template_id?: string | null;
  /** Active version when deployed */
  active_version_id?: string | null;
  /** Whether users may provision it (a template with no settings row is enabled). Independent of deployed: disabling hides a live template, deploying a disabled one keeps it hidden. */
  enabled?: boolean;
  /** Operator-edited on disk, so no longer re-synced from the repo */
  customized?: boolean;
  /** Workspaces currently on this template */
  workspace_count?: number;
  /** Workspaces of this template counting against its seat quota — the same rule the quota itself enforces (a start build in an active state). */
  running_workspace_count?: number;
}

/**
 * Every workspace template the deployment ships, deployed or not.
 */
export interface TemplateCatalogResponse {
  templates?: TemplateCatalogEntry[];
  /** False when the backend cannot read the templates directory, in which case only already-deployed templates are listed. */
  templates_dir_available?: boolean;
}

/**
 * One coder-home-* / coder-scratch-* docker volume.
 */
export interface WorkspaceVolume {
  /** Docker volume name */
  name: string;
  /** 'home' (shared per user) or 'scratch' (per workspace) */
  kind: string;
  /** Size on disk; null when docker has not computed it */
  size_bytes?: number | null;
  /** A container currently mounts it — deletion will be refused */
  in_use?: boolean | null;
  /** Docker's creation timestamp */
  created_at?: string | null;
  /** Computor user this home belongs to */
  user_id?: string | null;
  /** Display name / email of that user */
  user_name?: string | null;
  /** For a scratch volume, the workspace it belongs to */
  workspace_name?: string | null;
  /** Nothing references it any more: the Coder user or workspace the name points at no longer exists. Safe to reclaim. */
  orphaned?: boolean;
}

/**
 * All workspace volumes with their sizes and owners.
 */
export interface WorkspaceVolumeListResponse {
  volumes?: WorkspaceVolume[];
  /** Sum of the known sizes */
  total_bytes?: number;
  /** Coder was unreachable, so owners could not be resolved and nothing is reported as orphaned (absence of an owner would be misleading) */
  unresolved?: boolean;
}

/**
 * Per-template settings row (see model.workspace.WorkspaceTemplateSettings).
 */
export interface WorkspaceTemplateSettingsSchema {
  /** Coder template name (e.g. 'vscode-workspace') */
  template_name: string;
  /** Whether non-managers may see and provision this template; disabling hides it from listings and blocks new workspaces, existing ones keep running */
  enabled?: boolean;
  /** Container memory cap in MiB applied at push time; null/0 = unlimited */
  memory_mb?: number | null;
  /** Relative CPU weight applied at push time; null/0 = Docker default */
  cpu_shares?: number | null;
  /** Max concurrently running workspaces of this template across all users; null = unlimited, 0 freezes the template */
  max_running_workspaces?: number | null;
  /** Whether workspaces of this template may use sudo/su. The CEILING: a course can narrow it further but never grant root the template denies. Applied at the next template push. */
  allow_root?: boolean;
  /** Whether workspaces of this template reach the internet. The CEILING, same narrowing rule as allow_root. Applied at the next template push. */
  allow_internet?: boolean;
  /** Extra Terraform variable overrides pushed as --variable (only to templates that declare them) */
  template_variables?: Record<string, string>;
  /** Last settings change */
  updated_at?: string | null;
}

/**
 * Upsert payload for a template's settings.
 */
export interface WorkspaceTemplateSettingsUpdate {
  enabled?: boolean;
  memory_mb?: number | null;
  /** 0 = Docker default; Docker requires values >= 2 otherwise */
  cpu_shares?: number | null;
  max_running_workspaces?: number | null;
  /** Grant sudo/su in this template's workspaces (ceiling) */
  allow_root?: boolean;
  /** Allow internet egress from this template's workspaces (ceiling) */
  allow_internet?: boolean;
  template_variables?: Record<string, string>;
}

/**
 * All stored per-template settings rows.
 */
export interface TemplateSettingsListResponse {
  settings?: WorkspaceTemplateSettingsSchema[];
}

/**
 * One editable file of a template directory.
 */
export interface TemplateFile {
  name: string;
  content: string;
}

/**
 * Editable files of a deployed template directory.
 */
export interface TemplateFilesResponse {
  /** Coder template name */
  template_name: string;
  /** Template directory name under the templates root */
  dir_name: string;
  /** True when the .computor-managed marker is absent: the deployed template is operator-customized and no longer auto-synced from the repo */
  customized: boolean;
  files?: TemplateFile[];
}

/**
 * New content for one template file.
 */
export interface TemplateFileUpdateRequest {
  content: string;
}

/**
 * Result of a template file write / restore-managed action.
 */
export interface TemplateFileActionResponse {
  success: boolean;
  message: string;
  customized: boolean;
}

/**
 * One Terraform variable declared by a template (settings-override pick-list).
 */
export interface TemplateVariable {
  name: string;
  /** Declared type (string | number | bool | …) */
  type?: string | null;
  /** Declared default; masked (null) for sensitive variables */
  default?: unknown | null;
  has_default?: boolean;
  description?: string | null;
  sensitive?: boolean;
  /** Owned by the deployment (push pipeline, environment, or infrastructure wiring) — cannot be overridden by managers */
  managed?: boolean;
  managed_reason?: string | null;
  /** The .tf file declaring this variable */
  file: string;
}

/**
 * Declared variables of a deployed template.
 */
export interface TemplateVariablesResponse {
  template_name: string;
  dir_name: string;
  customized: boolean;
  variables?: TemplateVariable[];
}

/**
 * What happened to one workspace when a rotated credential was pushed.
 */
export interface WorkspaceCredentialOutcome {
  workspace_name: string;
  success?: boolean;
  /** Why it failed, or why it was skipped */
  error?: string | null;
}

/**
 * Result of rotating a user's workspace app credential.
 */
export interface WorkspaceCredentialRotationResponse {
  user_id: string;
  /** Key version now in effect */
  key_version: number;
  rotated_at?: string | null;
  /** False when no push was attempted — Coder disabled, or the user has no Coder account. The version bump still revoked the old credential. */
  pushed?: boolean;
  outcomes?: WorkspaceCredentialOutcome[];
  succeeded?: number;
  failed?: number;
}

/**
 * A user with their workspace roles.
 */
export interface WorkspaceRoleUser {
  user_id: string;
  email: string | null;
  username: string | null;
  given_name: string | null;
  family_name: string | null;
  roles?: string[];
}

/**
 * Request to assign a workspace role by email.
 */
export interface WorkspaceRoleAssign {
  email: string;
  role_id: string;
}

/**
 * Request to provision a workspace.
 */
export interface WorkspaceProvisionRequest {
  /** Target user email. If omitted, provisions for the current user. */
  email?: string | null;
  /** Workspace template name. Validated against the templates available in Coder; omit for the server default. */
  template?: string | null;
  /** Custom workspace name. Defaults to a name derived from the template. */
  workspace_name?: string | null;
  /** Home volume mode: 'shared' (per-user home volume) or 'scratch' (throwaway per-workspace volume). Full provisioners only; self-provisioning always uses the template default (shared). */
  home_mode?: string | null;
}



export type WorkspaceStatus = "pending" | "starting" | "running" | "stopping" | "stopped" | "failed" | "canceling" | "canceled" | "deleting" | "deleted";

export type WorkspaceBuildStatus = "pending" | "starting" | "running" | "stopping" | "stopped" | "succeeded" | "failed" | "canceling" | "canceled" | "deleting";