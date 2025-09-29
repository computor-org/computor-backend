/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Auth

 */



export interface MessageAuthor {
  /** Author's given name */
  given_name?: string | null;
  /** Author's family name */
  family_name?: string | null;
}

export interface GradingAuthor {
  /** Author's given name */
  given_name?: string | null;
  /** Author's family name */
  family_name?: string | null;
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

export interface OrganizationUpdateTokenQuery {
  type: string;
}

export interface OrganizationUpdateTokenUpdate {
  token: string;
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
 * Response after successful SSO authentication.
 */
export interface SSOAuthResponse {
  /** User ID */
  user_id: string;
  /** Account ID */
  account_id: string;
  /** Access token if available */
  access_token?: string | null;
  /** Whether this is a new user */
  is_new_user: boolean;
}

/**
 * Token refresh request.
 */
export interface TokenRefreshRequest {
  /** Refresh token from initial authentication */
  refresh_token: string;
  /** Authentication provider */
  provider?: string;
}

/**
 * Response after successful token refresh.
 */
export interface TokenRefreshResponse {
  /** New access token */
  access_token: string;
  /** Token expiration time in seconds */
  expires_in?: number | null;
  /** New refresh token if rotated */
  refresh_token?: string | null;
}