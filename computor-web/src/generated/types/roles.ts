/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Roles

 */



export interface RoleGet {
  /** Role unique identifier */
  id: string;
  /** Role title */
  title?: string | null;
  /** Role description */
  description?: string | null;
  /** Whether this is a built-in role */
  builtin: boolean;
}

export interface RoleList {
  /** Role unique identifier */
  id: string;
  /** Role title */
  title?: string | null;
  /** Whether this is a built-in role */
  builtin: boolean;
}

export interface RoleQuery {
  skip?: number | null;
  limit?: number | null;
  /** Filter by role ID */
  id?: string | null;
  /** Filter by role title */
  title?: string | null;
  /** Filter by description */
  description?: string | null;
  /** Filter by builtin status */
  builtin?: boolean | null;
}

export interface RoleClaimGet {
  role_id: string;
  claim_type: string;
  claim_value: string;
  properties?: any | null;
}

export interface RoleClaimList {
  role_id: string;
  claim_type: string;
  claim_value: string;
}

export interface RoleClaimQuery {
  skip?: number | null;
  limit?: number | null;
  role_id?: string | null;
  claim_type?: string | null;
  claim_value?: string | null;
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
  /** Workspace template to use */
  template?: WorkspaceTemplate;
  /** Custom workspace name */
  workspace_name?: string | null;
}



export type WorkspaceTemplate = "python-workspace" | "matlab-workspace";