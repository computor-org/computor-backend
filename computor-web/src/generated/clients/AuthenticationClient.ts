/**
 * Auto-generated client for AuthenticationClient.
 * Endpoint: /auth
 */

import type { GitLabRegisterRequest, GitLabRegisterResponse, LocalTokenRefreshRequest, LocalTokenRefreshResponse, LogoutResponse, ProviderInfo, TokenRefreshRequest, TokenRefreshResponse } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class AuthenticationClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/auth');
  }

  /**
   * List All Plugins
   * List all available plugins (admin only).
   * Shows both enabled and disabled plugins with full metadata.
   */
  async listAllPluginsAuthAdminPluginsGet(): Promise<Record<string, unknown> & Record<string, unknown>> {
    return this.client.get<Record<string, unknown> & Record<string, unknown>>(this.buildPath('admin', 'plugins'));
  }

  /**
   * Reload Plugins
   * Reload all plugins (admin only).
   */
  async reloadPluginsAuthAdminPluginsReloadPost(): Promise<Record<string, unknown> & Record<string, unknown>> {
    return this.client.post<Record<string, unknown> & Record<string, unknown>>(this.buildPath('admin', 'plugins', 'reload'));
  }

  /**
   * Disable Plugin
   * Disable a plugin (admin only).
   */
  async disablePluginAuthAdminPluginsPluginNameDisablePost({ pluginName }: { pluginName: string }): Promise<Record<string, unknown> & Record<string, unknown>> {
    return this.client.post<Record<string, unknown> & Record<string, unknown>>(this.buildPath('admin', 'plugins', pluginName, 'disable'));
  }

  /**
   * Enable Plugin
   * Enable a plugin (admin only).
   */
  async enablePluginAuthAdminPluginsPluginNameEnablePost({ pluginName }: { pluginName: string }): Promise<Record<string, unknown> & Record<string, unknown>> {
    return this.client.post<Record<string, unknown> & Record<string, unknown>>(this.buildPath('admin', 'plugins', pluginName, 'enable'));
  }

  /**
   * Register Via Gitlab
   * Provision (or reset) a user's Keycloak login using a GitLab PAT as proof.
   * Idempotent by design: if the Keycloak user already exists, its password is
   * reset — so a user who forgot their credentials simply re-runs this with a
   * new password. The Keycloak account links to the existing computor user on
   * first SSO login via the email match in handle_sso_callback.
   */
  async registerViaGitlabAuthGitlabRegisterPost({ userId, body }: { userId?: string | null; body: GitLabRegisterRequest }): Promise<GitLabRegisterResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<GitLabRegisterResponse>(this.buildPath('gitlab', 'register'), body, { params: queryParams });
  }

  /**
   * Logout
   * Logout from current session.
   * This endpoint works with any authentication type:
   * - Local authentication (Bearer tokens)
   * - SSO authentication (provider tokens)
   * The Bearer token from the Authorization header will be invalidated.
   * Cookies will also be cleared.
   */
  async logoutAuthLogoutPost({ userId }: { userId?: string | null }): Promise<LogoutResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<LogoutResponse>(this.buildPath('logout'), { params: queryParams });
  }

  /**
   * List Providers
   * List available authentication providers.
   * Returns all enabled authentication providers with their metadata.
   */
  async listProvidersAuthProvidersGet(): Promise<ProviderInfo[]> {
    return this.client.get<ProviderInfo[]>(this.buildPath('providers'));
  }

  /**
   * Refresh Token
   * Refresh SSO access token using refresh token.
   * Cookie-based clients (the web UI) omit ``refresh_token`` from the body and
   * send the HttpOnly ``ct_refresh_token`` cookie instead — JS cannot read that
   * cookie, so we read it server-side. On success we re-set both HttpOnly cookies
   * so the browser session is renewed (otherwise the original ``ct_access_token``
   * max_age expires ~1h after login regardless of activity and the user is logged
   * out, and the rotated refresh token never reaches the client).
   * Requires authentication to ensure only the token owner can refresh it.
   */
  async refreshTokenAuthRefreshPost({ userId, body }: { userId?: string | null; body: TokenRefreshRequest }): Promise<TokenRefreshResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<TokenRefreshResponse>(this.buildPath('refresh'), body, { params: queryParams });
  }

  /**
   * Refresh Local Token
   * Refresh local access token using refresh token.
   * This endpoint allows users to refresh their session token for local
   * (username/password) authentication using the refresh token obtained
   * during initial login.
   * Authentication is not required for this endpoint since the access token
   * may be expired. The refresh token itself is validated to ensure security.
   */
  async refreshLocalTokenAuthRefreshLocalPost({ userId, body }: { userId?: string | null; body: LocalTokenRefreshRequest }): Promise<LocalTokenRefreshResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<LocalTokenRefreshResponse>(this.buildPath('refresh', 'local'), body, { params: queryParams });
  }

  /**
   * Sso Success
   * Default success page after SSO authentication.
   */
  async ssoSuccessAuthSuccessGet(): Promise<void> {
    return this.client.get<void>(this.buildPath('success'));
  }

  /**
   * Verify Coder Access
   * Traefik ForwardAuth endpoint for Coder workspace access control.
   * This endpoint is called by Traefik before forwarding requests to code-server workspaces.
   * It verifies that:
   * 1. The user is authenticated (via Bearer token, Basic auth, or API token)
   * 2. The authenticated user matches the user ID in the workspace URL
   * URL Format: /coder/u{user_id}/{workspace_name}/...
   * Example: /coder/u0232de59-e05d-4bc2-898f-b879c06/{workspace}/
   * The 'u' prefix is required for Coder username compatibility, so we strip it to get the actual user ID.
   * Returns:
   * - 200 OK: User is authorized to access this workspace
   * - 401 Unauthorized: User is not authenticated
   * - 403 Forbidden: User is authenticated but not authorized for this workspace
   */
  async verifyCoderAccessAuthVerifyCoderAccessGet(): Promise<void> {
    return this.client.get<void>(this.buildPath('verify-coder-access'));
  }

  /**
   * Handle Callback
   * Handle OAuth callback from provider.
   * Exchanges the authorization code for tokens and creates/updates user account.
   */
  async handleCallbackAuthProviderCallbackGet({ provider, code, state, userId }: { provider: string; code: string; state?: string | null; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      code,
      state,
      user_id: userId,
    };
    return this.client.get<void>(this.buildPath(provider, 'callback'), { params: queryParams });
  }

  /**
   * Initiate Login
   * Initiate SSO login for a specific provider.
   * Redirects the user to the provider's login page.
   */
  async initiateLoginAuthProviderLoginGet({ provider, redirectUri }: { provider: string; redirectUri?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      redirect_uri: redirectUri,
    };
    return this.client.get<void>(this.buildPath(provider, 'login'), { params: queryParams });
  }

  /**
   * Sso Logout
   * SSO logout: clears the backend session cookies AND ends the Keycloak SSO
   * session by redirecting the browser to the provider's end_session_endpoint.
   * The frontend should navigate to this URL (browser redirect, not XHR) so
   * the cookie-clearing + Keycloak end-session flow completes properly.
   * Designed to be tolerant of an already-expired or missing local session —
   * we always clear cookies and forward to Keycloak so the user is fully
   * signed out at the IdP.
   */
  async ssoLogoutAuthProviderLogoutGet({ provider, postLogoutRedirectUri }: { provider: string; postLogoutRedirectUri?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      post_logout_redirect_uri: postLogoutRedirectUri,
    };
    return this.client.get<void>(this.buildPath(provider, 'logout'), { params: queryParams });
  }
}
