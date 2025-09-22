/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Users

 */



import type { StudentProfileGet } from './common';



/**
 * Request payload to set or update a provider account for a course member.
 */
export interface CourseMemberProviderAccountUpdate {
  /** Account identifier on the external provider (e.g., GitLab username) */
  provider_account_id: string;
  /** Personal access token or credential to verify provider ownership */
  provider_access_token?: string | null;
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

export interface UserCreate {
  /** User ID (UUID will be generated if not provided) */
  id?: string | null;
  /** User's given name */
  given_name?: string | null;
  /** User's family name */
  family_name?: string | null;
  /** User's email address */
  email?: string | null;
  /** User number/identifier */
  number?: string | null;
  /** Type of user account */
  user_type?: UserTypeEnum | null;
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
  /** User number/identifier */
  number?: string | null;
  /** Type of user account */
  user_type?: UserTypeEnum | null;
  /** Unique username */
  username?: string | null;
  /** Additional user properties */
  properties?: any | null;
  /** Timestamp when user was archived */
  archived_at?: string | null;
  /** Associated student profiles */
  student_profiles?: StudentProfileGet[];
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
  /** Type of user account */
  user_type?: UserTypeEnum | null;
  /** Unique username */
  username?: string | null;
  /** Archive timestamp */
  archived_at?: string | null;
}

export interface UserUpdate {
  /** User's given name */
  given_name?: string | null;
  /** User's family name */
  family_name?: string | null;
  /** User's email address */
  email?: string | null;
  /** User number/identifier */
  number?: string | null;
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
  number?: string | null;
  user_type?: UserTypeEnum | null;
  properties?: any | null;
  archived?: boolean | null;
  username?: string | null;
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
  properties?: string | null;
}

export interface UserPassword {
  username: string;
  password: string;
}

/**
 * User registration request.
 */
export interface UserRegistrationRequest {
  /** Username */
  username: string;
  /** Email address */
  email: string;
  /** Password */
  password: string;
  /** First name */
  given_name: string;
  /** Last name */
  family_name: string;
  /** Authentication provider to register with */
  provider?: string;
  /** Send email verification */
  send_verification_email?: boolean;
}

/**
 * Response after successful user registration.
 */
export interface UserRegistrationResponse {
  /** User ID in Computor */
  user_id: string;
  /** User ID in authentication provider */
  provider_user_id: string;
  /** Username */
  username: string;
  /** Email address */
  email: string;
  /** Success message */
  message: string;
}



export type UserTypeEnum = "user" | "token";