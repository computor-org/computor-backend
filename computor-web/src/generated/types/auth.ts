/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Auth

 */



import type { GitLabPATCredentials } from './common';



/**
 * Request to login to Coder.
 */
export interface CoderLoginRequest {
  password: string;
  redirect_url?: string | null;
}

/**
 * Query parameters for updating organization token.
 */
export interface OrganizationUpdateTokenQuery {
  /** Token type (e.g., 'gitlab', 'github') */
  type: string;
}

/**
 * Payload for updating organization provider token.
 */
export interface OrganizationUpdateTokenUpdate {
  /** Provider access token */
  token: string;
}

export interface AuthConfig {
}

export interface GLPAuthConfig {
  url: string;
  token: string;
}

export interface BasicAuthConfig {
  username: string;
  password: string;
}

/**
 * Request model for local username/password login.
 */
export interface LocalLoginRequest {
  /** Username or email */
  username: string;
  /** Password */
  password: string;
}

/**
 * Response model after successful local login.
 */
export interface LocalLoginResponse {
  /** Bearer access token for API requests */
  access_token: string;
  /** Refresh token to obtain new access token */
  refresh_token: string;
  /** Access token expiration time in seconds */
  expires_in: number;
  /** User ID */
  user_id: string;
  /** Token type */
  token_type?: string;
}

/**
 * Request model for logout.
 */
export interface LogoutRequest {
  /** Provider name for SSO logout (optional) */
  provider?: string | null;
}

/**
 * Response model after successful logout.
 */
export interface LogoutResponse {
  /** Logout status message */
  message: string;
  /** Provider that was logged out from */
  provider?: string | null;
}

/**
 * Request model for refreshing local session token.
 */
export interface LocalTokenRefreshRequest {
  /** Refresh token from initial authentication */
  refresh_token: string;
}

/**
 * Response model after successful token refresh.
 */
export interface LocalTokenRefreshResponse {
  /** New Bearer access token */
  access_token: string;
  /** Token expiration time in seconds */
  expires_in: number;
  /** New refresh token if rotated */
  refresh_token?: string | null;
  /** Token type */
  token_type?: string;
}

/**
 * Information about an authentication provider.
 */
export interface ProviderInfo {
  /** Provider name */
  name: string;
  /** Display name */
  display_name: string;
  /** Authentication type */
  type: string;
  /** Whether provider is enabled */
  enabled: boolean;
  /** Login URL if applicable */
  login_url?: string | null;
}

/**
 * Login request for SSO.
 */
export interface LoginRequest {
  /** Provider name */
  provider: string;
  /** Redirect URI after login */
  redirect_uri?: string | null;
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

/**
 * Token refresh request for SSO.
 */
export interface TokenRefreshRequest {
  /** Refresh token from initial authentication */
  refresh_token: string;
  /** Authentication provider */
  provider?: string;
}

/**
 * Response after successful SSO token refresh.
 */
export interface TokenRefreshResponse {
  /** New access token */
  access_token: string;
  /** Token expiration time in seconds */
  expires_in?: number | null;
  /** New refresh token if rotated */
  refresh_token?: string | null;
}

/**
 * Author information for a message.
 */
export interface MessageAuthor {
  /** User ID of the author */
  id: string;
  /** Author's given name */
  given_name?: string | null;
  /** Author's family name */
  family_name?: string | null;
}

/**
 * Course member context for the message author (when message is in a course context).
 */
export interface MessageAuthorCourseMember {
  /** Course member ID */
  id: string;
  /** Role of the author in the course (e.g., '_student', '_tutor', '_lecturer') */
  course_role_id: string;
  /** Course ID */
  course_id: string;
}

export interface GradingAuthor {
  /** Author's given name */
  given_name?: string | null;
  /** Author's family name */
  family_name?: string | null;
}

/**
 * Alternative authentication via external provider for password initialization.
 */
export interface ProviderAuthCredentials {
  /** Authentication method */
  method: "gitlab_pat";
  /** Provider-specific credentials */
  credentials: GitLabPATCredentials;
}

/**
 * DTO for creating a new API token.
 * 
 * The actual token value is generated server-side and returned once.
 * Store it securely - it cannot be retrieved later!
 */
export interface ApiTokenCreate {
  /** Human-readable token name */
  name: string;
  /** Token description/purpose */
  description?: string | null;
  /** User ID that owns this token */
  user_id: string;
  /** Token scopes (e.g., ['read:courses', 'write:results']) */
  scopes?: string[];
  /** Token expiration date (null = never expires) */
  expires_at?: string | null;
  /** Additional properties */
  properties?: Record<string, any> | null;
}

/**
 * Admin-only DTO for creating API tokens with predefined values.
 * 
 * Used for initial deployment where tokens need to be known in advance.
 * Regular users should use ApiTokenCreate instead.
 */
export interface ApiTokenAdminCreate {
  /** Human-readable token name */
  name: string;
  /** Token description/purpose */
  description?: string | null;
  /** User ID that owns this token */
  user_id: string;
  /** Predefined token value (must start with 'ctp_') */
  predefined_token: string;
  /** Token scopes (e.g., ['read:courses', 'write:results']) */
  scopes?: string[];
  /** Token expiration date (null = never expires) */
  expires_at?: string | null;
  /** Additional properties */
  properties?: Record<string, any> | null;
}

/**
 * Response after creating an API token.
 * 
 * IMPORTANT: The token field contains the actual token value.
 * This is the ONLY time it will be visible - store it securely!
 */
export interface ApiTokenCreateResponse {
  /** Token ID */
  id: string;
  /** The actual token value (STORE SECURELY - shown only once!) */
  token: string;
  name: string;
  description?: string | null;
  user_id: string;
  /** Token prefix for identification (e.g., 'ctp_a1b2c3d4') */
  token_prefix: string;
  scopes: string[];
  expires_at?: string | null;
  created_at: string;
}

/**
 * DTO for updating an API token.
 */
export interface ApiTokenUpdate {
  name?: string | null;
  description?: string | null;
  scopes?: string[] | null;
  expires_at?: string | null;
  properties?: Record<string, any> | null;
}

/**
 * DTO for revoking an API token.
 */
export interface ApiTokenRevoke {
  /** Reason for revocation */
  revocation_reason?: string | null;
}

/**
 * DTO for retrieving an API token.
 * 
 * Note: The actual token value is NEVER returned after creation.
 * Only metadata and the prefix are available.
 */
export interface ApiTokenGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  /** Token UUID */
  id: string;
  name: string;
  description?: string | null;
  user_id: string;
  /** First 12 characters for identification */
  token_prefix: string;
  scopes: string[];
  expires_at?: string | null;
  last_used_at?: string | null;
  /** Number of times this token has been used */
  usage_count?: number;
  revoked_at?: string | null;
  revocation_reason?: string | null;
}

/**
 * DTO for listing API tokens.
 */
export interface ApiTokenList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  items: ApiTokenGet[];
}

/**
 * DTO for querying API tokens.
 */
export interface ApiTokenQuery {
  skip?: number | null;
  limit?: number | null;
  /** Filter by user ID */
  user_id?: string | null;
  /** Filter by revoked status (null = all, true = revoked, false = active) */
  revoked?: boolean | null;
  /** Filter by expiration status */
  expired?: boolean | null;
  /** Filter by required scopes (token must have all) */
  scopes?: string[] | null;
}