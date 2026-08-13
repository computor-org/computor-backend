/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Users

 */



import type { ProfileGet, StudentProfileGet } from './common';



/**
 * Request payload to set or update a provider account for a course member.
 */
export interface CourseMemberProviderAccountUpdate {
  /** Account identifier on the external provider (e.g., GitLab username) */
  provider_account_id: string;
  /** Personal access token or credential to verify provider ownership */
  provider_access_token?: string | null;
}

export interface AccountCreate {
  /** Authentication provider name */
  provider: string;
  /** Type of authentication account */
  type: string;
  /** Account ID from the provider */
  provider_account_id: string;
  /** Associated user ID */
  user_id: string;
  /** Provider-specific properties */
  properties?: any | null;
}

export interface AccountGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  /** Account unique identifier */
  id: string;
  /** Authentication provider name */
  provider: string;
  /** Type of authentication account */
  type: string;
  /** Account ID from the provider */
  provider_account_id: string;
  /** Associated user ID */
  user_id: string;
  /** Built-in identity account (SSO / Git server) that the user cannot unlink */
  builtin?: boolean;
  /** Provider-specific properties */
  properties?: any | null;
}

export interface AccountList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  /** Account unique identifier */
  id: string;
  /** Authentication provider name */
  provider: string;
  /** Type of authentication account */
  type: string;
  /** Account ID from the provider */
  provider_account_id: string;
  /** Associated user ID */
  user_id: string;
  /** Built-in identity account (SSO / Git server) that the user cannot unlink */
  builtin?: boolean;
}

export interface AccountUpdate {
  /** Authentication provider name */
  provider?: string | null;
  /** Type of authentication account */
  type?: string | null;
  /** Account ID from the provider */
  provider_account_id?: string | null;
  /** Provider-specific properties */
  properties?: any | null;
}

export interface AccountQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  provider?: string | null;
  type?: string | null;
  provider_account_id?: string | null;
  user_id?: string | null;
}

/**
 * A supported external provider that can be linked to a user account.
 * 
 * Returned by GET /accounts/providers so the UI can render the correct linking
 * form. Currently backed by a static list in the backend; the shape is stable
 * if that becomes a DB query later.
 */
export interface AccountProvider {
  /** Short provider key, e.g. 'gitlab' */
  id: string;
  /** Human-readable provider name */
  display_name: string;
  /** What linking this provider is used for */
  description: string;
  /** Value written to account.provider, e.g. 'gitlab.com' */
  provider: string;
  /** Value written to account.type, e.g. 'gitlab' */
  type: string;
  /** Label for the provider_account_id input */
  field_label: string;
  /** Placeholder for the provider_account_id input */
  placeholder: string;
}

/**
 * User manager request to reset a user's password (sets to NULL).
 */
export interface UserManagerResetPasswordRequest {
  /** Target user ID to reset */
  user_id: string;
  /** User manager's own password for verification */
  manager_password: string;
}

export interface UserGroupCreate {
  /** User ID */
  user_id: string;
  /** Group ID */
  group_id: string;
  /** Whether this is a transient membership */
  transient?: boolean | null;
}

export interface UserGroupGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  /** User ID */
  user_id: string;
  /** Group ID */
  group_id: string;
  /** Whether this is transient membership */
  transient?: boolean | null;
}

export interface UserGroupList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  /** User ID */
  user_id: string;
  /** Group ID */
  group_id: string;
  /** Whether this is transient membership */
  transient?: boolean | null;
}

export interface UserGroupUpdate {
  /** Whether this is transient membership */
  transient?: boolean | null;
}

export interface UserGroupQuery {
  skip?: number | null;
  limit?: number | null;
  /** Filter by user ID */
  user_id?: string | null;
  /** Filter by group ID */
  group_id?: string | null;
  /** Filter by transient status */
  transient?: boolean | null;
}

export interface UserCreate {
  /** User ID (UUID will be generated if not provided) */
  id?: string | null;
  /** User's given name */
  given_name?: string | null;
  /** User's family name */
  family_name?: string | null;
  /** User's email address */
  email?: string | null;
  /** Additional user properties */
  properties?: any | null;
}

export interface UserGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  /** User unique identifier */
  id: string;
  /** User's given name */
  given_name?: string | null;
  /** User's family name */
  family_name?: string | null;
  /** User's email address */
  email?: string | null;
  /** Additional user properties */
  properties?: any | null;
  /** Timestamp when user was archived */
  archived_at?: string | null;
  /** Whether this is a service account */
  is_service: boolean;
  /** Timestamp when the user was banned (null = not banned) */
  banned_at?: string | null;
  /** Optional reason recorded when the user was banned */
  ban_reason?: string | null;
  /** Associated student profiles */
  student_profiles?: StudentProfileGet[];
  /** User profile */
  profile?: ProfileGet | null;
  /** User's global roles */
  user_roles?: UserRoleGet[];
  /** Whether the user is currently banned from authenticating. */
  banned: boolean;
}

export interface UserList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  /** User unique identifier */
  id: string;
  /** User's given name */
  given_name?: string | null;
  /** User's family name */
  family_name?: string | null;
  /** User's email address */
  email?: string | null;
  /** Archive timestamp */
  archived_at?: string | null;
  /** Whether this is a service account */
  is_service: boolean;
  /** Timestamp when the user was banned (null = not banned) */
  banned_at?: string | null;
  /** Whether the user is currently banned from authenticating. */
  banned: boolean;
}

export interface UserUpdate {
  /** User's given name */
  given_name?: string | null;
  /** User's family name */
  family_name?: string | null;
  /** User's email address */
  email?: string | null;
  /** Additional user properties */
  properties?: any | null;
}

export interface UserQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  given_name?: string | null;
  family_name?: string | null;
  email?: string | null;
  archived?: boolean | null;
  is_service?: boolean | null;
  banned?: boolean | null;
  search?: string | null;
}

/**
 * Optional payload for the ban endpoint.
 */
export interface UserBanRequest {
  /** Reason for the ban (stored for audit, shown to administrators) */
  reason?: string | null;
}

/**
 * Request to absorb a pre-provisioned user into the addressed user.
 * 
 * The addressed user (path parameter) is the keeper — the real, logged-in
 * account. ``source_user_id`` names the pre-provisioned row (created by a
 * course roster import) that is absorbed and deleted. The operation is
 * refused unless the source user has never authenticated.
 */
export interface UserConnectRequest {
  /** Id of the pre-provisioned user to absorb; this row is deleted on success */
  source_user_id: string;
  /** Validate and return the merge plan without changing anything */
  dry_run?: boolean;
}

/**
 * One course membership affected by a user-connect operation.
 */
export interface UserConnectCourseMove {
  /** Course the membership belongs to */
  course_id: string;
  /** Course title, for display */
  course_title?: string | null;
  /** 'moved' (membership re-pointed to the keeper) or 'duplicate_removed' (keeper already enrolled; the source's empty membership was removed) */
  action: string;
  /** Whether the source membership's course group was copied onto the keeper's membership */
  group_carried_over?: boolean;
}

/**
 * One student profile affected by a user-connect operation.
 */
export interface UserConnectProfileMove {
  /** Organization the profile is scoped to */
  organization_id: string;
  /** Organization title, for display */
  organization_title?: string | null;
  /** Student email the keeper's profile carries after the merge (the imported address) */
  student_email?: string | null;
  /** 'moved' (profile re-pointed to the keeper) or 'merged' (keeper already had a profile for the organization; fields were merged into it) */
  action: string;
}

/**
 * Outcome (or dry-run plan) of connecting a pre-provisioned user to a real one.
 */
export interface UserConnectResponse {
  /** True if nothing was changed and this is only the plan */
  dry_run: boolean;
  /** The absorbed (pre-provisioned) user */
  source_user_id: string;
  /** The keeper the data was moved onto */
  target_user_id: string;
  /** Email of the absorbed user (the imported address) */
  source_email?: string | null;
  /** Course memberships moved or resolved */
  course_memberships?: UserConnectCourseMove[];
  /** Student profiles moved or merged */
  student_profiles?: UserConnectProfileMove[];
  /** System roles the keeper gained from the source user */
  roles_merged?: string[];
  /** Manually linked provider accounts re-pointed to the keeper */
  accounts_moved?: number;
  /** Messages addressed to or mentioning the source user re-pointed to the keeper */
  messages_repointed?: number;
  /** Whether the source user row was deleted (always true on a non-dry-run success) */
  source_deleted?: boolean;
}

/**
 * Password update request for user endpoints.
 */
export interface UserPassword {
  /** New password */
  password: string;
  /** Old password (required for non-admin password changes) */
  password_old?: string | null;
}

/**
 * Per-scope role memberships for the current authenticated user.
 * 
 * Mirrors the scope-namespace slice of ``Principal.claims.dependent``
 * so a client can pre-gate UI against the same data the backend uses
 * for authorization. Each map is keyed by ``scope_id`` and lists every
 * role label the user holds on that scope (a user can hold more than
 * one role on the same scope).
 * 
 * Admins do not have explicit per-scope claims — instead ``is_admin``
 * is true and the server bypasses scope checks entirely. Treat that as
 * "every role on every scope".
 */
export interface UserScopes {
  /** Whether the user is a system admin (bypasses all scope checks). */
  is_admin: boolean;
  /** organization_id -> [role labels held by the user on that organization]. */
  organization?: Record<string, string[]>;
  /** course_family_id -> [role labels held by the user on that course family]. */
  course_family?: Record<string, string[]>;
  /** course_id -> [role labels held by the user on that course]. */
  course?: Record<string, string[]>;
}

export interface UserRoleCreate {
  user_id: string;
  role_id: string;
}

export interface UserRoleGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  user_id: string;
  role_id: string;
}

export interface UserRoleList {
  user_id: string;
  role_id: string;
}

export interface UserRoleUpdate {
  role_id: string;
}

export interface UserRoleQuery {
  skip?: number | null;
  limit?: number | null;
  user_id?: string | null;
  role_id?: string | null;
}