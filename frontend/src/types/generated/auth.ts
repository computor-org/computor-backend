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

export interface OrganizationUpdateTokenQuery {
  type: string;
}

export interface OrganizationUpdateTokenUpdate {
  token: string;
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
 * OAuth callback parameters.
 */
export interface CallbackRequest {
  /** Authorization code */
  code: string;
  /** State parameter */
  state?: string | null;
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