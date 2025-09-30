/**
 * Auto-generated client for AuthenticationClient.
 * Endpoint: /auth
 */

import type { LocalLoginRequest, LocalLoginResponse, LocalTokenRefreshRequest, LocalTokenRefreshResponse, LogoutResponse, ProviderInfo, TokenRefreshRequest, TokenRefreshResponse, UserRegistrationRequest, UserRegistrationResponse } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class AuthenticationClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/auth');
  }

  /**
   * Login With Credentials
   * Login with username and password to obtain Bearer tokens.
   * This endpoint authenticates users with local credentials and returns
   * access and refresh tokens that can be used for subsequent API requests.
   * The access token should be included in the Authorization header as:
   * `Authorization: Bearer <access_token>`
   */
  async loginWithCredentialsAuthLoginPost({ body }: { body: LocalLoginRequest }): Promise<LocalLoginResponse> {
    return this.client.post<LocalLoginResponse>(this.buildPath('login'), body);
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
   * Handle Callback
   * Handle OAuth callback from provider.
   * Exchanges the authorization code for tokens and creates/updates user account.
   */
  async handleCallbackAuthProviderCallbackGet({ provider, code, state }: { provider: string; code: string; state?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      code,
      state,
    };
    return this.client.get<void>(this.buildPath(provider, 'callback'), { params: queryParams });
  }

  /**
   * Sso Success
   * Default success page after SSO authentication.
   */
  async ssoSuccessAuthSuccessGet(): Promise<void> {
    return this.client.get<void>(this.buildPath('success'));
  }

  /**
   * Logout
   * Logout from current session.
   * This endpoint works with any authentication type:
   * - Local authentication (Bearer tokens)
   * - SSO authentication (provider tokens)
   * The Bearer token from the Authorization header will be invalidated.
   */
  async logoutAuthLogoutPost(): Promise<LogoutResponse> {
    return this.client.post<LogoutResponse>(this.buildPath('logout'));
  }

  /**
   * List All Plugins
   * List all available plugins (admin only).
   * Shows both enabled and disabled plugins with full metadata.
   */
  async listAllPluginsAuthAdminPluginsGet(): Promise<void> {
    return this.client.get<void>(this.buildPath('admin', 'plugins'));
  }

  /**
   * Enable Plugin
   * Enable a plugin (admin only).
   */
  async enablePluginAuthAdminPluginsPluginNameEnablePost({ pluginName }: { pluginName: string }): Promise<void> {
    return this.client.post<void>(this.buildPath('admin', 'plugins', pluginName, 'enable'));
  }

  /**
   * Disable Plugin
   * Disable a plugin (admin only).
   */
  async disablePluginAuthAdminPluginsPluginNameDisablePost({ pluginName }: { pluginName: string }): Promise<void> {
    return this.client.post<void>(this.buildPath('admin', 'plugins', pluginName, 'disable'));
  }

  /**
   * Reload Plugins
   * Reload all plugins (admin only).
   */
  async reloadPluginsAuthAdminPluginsReloadPost(): Promise<void> {
    return this.client.post<void>(this.buildPath('admin', 'plugins', 'reload'));
  }

  /**
   * Register User
   * Register a new user with SSO provider.
   * Creates user in both the authentication provider and local database.
   */
  async registerUserAuthRegisterPost({ body }: { body: UserRegistrationRequest }): Promise<UserRegistrationResponse> {
    return this.client.post<UserRegistrationResponse>(this.buildPath('register'), body);
  }

  /**
   * Refresh Local Token
   * Refresh local access token using refresh token.
   * This endpoint allows users to refresh their session token for local
   * (username/password) authentication using the refresh token obtained
   * during initial login.
   */
  async refreshLocalTokenAuthRefreshLocalPost({ body }: { body: LocalTokenRefreshRequest }): Promise<LocalTokenRefreshResponse> {
    return this.client.post<LocalTokenRefreshResponse>(this.buildPath('refresh', 'local'), body);
  }

  /**
   * Refresh Token
   * Refresh SSO access token using refresh token.
   * This endpoint allows users to refresh their session token using
   * the refresh token obtained during initial SSO authentication.
   */
  async refreshTokenAuthRefreshPost({ body }: { body: TokenRefreshRequest }): Promise<TokenRefreshResponse> {
    return this.client.post<TokenRefreshResponse>(this.buildPath('refresh'), body);
  }
}
