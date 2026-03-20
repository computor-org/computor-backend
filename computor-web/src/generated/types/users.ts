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
 * A user with their workspace roles.
 */
export interface WorkspaceRoleUser {
  user_id: string;
  email: any;
  username: any;
  given_name: any;
  family_name: any;
  roles?: string[];
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
  /** Unique username */
  username?: string | null;
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
  /** Unique username */
  username?: string | null;
  /** Additional user properties */
  properties?: any | null;
  /** Timestamp when user was archived */
  archived_at?: string | null;
  /** Whether this is a service account */
  is_service: boolean;
  /** Associated student profiles */
  student_profiles?: StudentProfileGet[];
  /** User profile */
  profile?: ProfileGet | null;
  /** User's global roles */
  user_roles?: UserRoleGet[];
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
  /** Unique username */
  username?: string | null;
  /** Archive timestamp */
  archived_at?: string | null;
  /** Whether this is a service account */
  is_service: boolean;
}

export interface UserUpdate {
  /** User's given name */
  given_name?: string | null;
  /** User's family name */
  family_name?: string | null;
  /** User's email address */
  email?: string | null;
  /** Unique username */
  username?: string | null;
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
  username?: string | null;
  is_service?: boolean | null;
}

/**
 * Password update request for user endpoints.
 */
export interface UserPassword {
  /** Target username (admin only, otherwise current user) */
  username?: string | null;
  /** New password */
  password: string;
  /** Old password (required for non-admin password changes) */
  password_old?: string | null;
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