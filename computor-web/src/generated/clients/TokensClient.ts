/**
 * Auto-generated client for TokensClient.
 * Endpoint: /api-tokens
 */

import type { ApiTokenAdminCreate, ApiTokenCreate, ApiTokenCreateResponse, ApiTokenGet, ApiTokenUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class TokensClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/api-tokens');
  }

  /**
   * List Tokens Endpoint
   * List API tokens.
   * Admins can list all tokens or filter by user_id.
   * Regular users can only list their own tokens.
   */
  async listTokensEndpointApiTokensGet({ includeRevoked, userId }: { includeRevoked?: boolean; userId?: string | null }): Promise<ApiTokenGet[]> {
    const queryParams: Record<string, unknown> = {
      include_revoked: includeRevoked,
      user_id: userId,
    };
    return this.client.get<ApiTokenGet[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Token Endpoint
   * Create a new API token.
   * Returns the full token string (only shown once - cannot be retrieved later).
   */
  async createTokenEndpointApiTokensPost({ userId, body }: { userId?: string | null; body: ApiTokenCreate }): Promise<ApiTokenCreateResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<ApiTokenCreateResponse>(this.basePath, body, { params: queryParams });
  }

  /**
   * Create Token Admin Endpoint
   * Create an API token with a predefined value (admin-only).
   * This endpoint is for initial deployment where tokens need to be known in advance.
   * Requires admin permissions. Regular users should use the standard token creation endpoint.
   */
  async createTokenAdminEndpointApiTokensAdminCreatePost({ userId, body }: { userId?: string | null; body: ApiTokenAdminCreate }): Promise<ApiTokenCreateResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<ApiTokenCreateResponse>(this.buildPath('admin', 'create'), body, { params: queryParams });
  }

  /**
   * Update Token Admin Endpoint
   * Update an API token (admin-only).
   * This endpoint is primarily for updating token scopes after course creation during deployment.
   * Requires admin permissions.
   */
  async updateTokenAdminEndpointApiTokensAdminTokenIdPatch({ tokenId, userId, body }: { tokenId: string; userId?: string | null; body: ApiTokenUpdate }): Promise<ApiTokenGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<ApiTokenGet>(this.buildPath('admin', tokenId), body, { params: queryParams });
  }

  /**
   * Revoke Token Endpoint
   * Revoke an API token.
   * The token will be immediately invalidated and cannot be used for authentication.
   */
  async revokeTokenEndpointApiTokensTokenIdDelete({ tokenId, reason, userId }: { tokenId: string; reason?: string | null; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      reason,
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(tokenId), { params: queryParams });
  }

  /**
   * Get Token Endpoint
   * Get API token details by ID (does not include the actual token).
   */
  async getTokenEndpointApiTokensTokenIdGet({ tokenId, userId }: { tokenId: string; userId?: string | null }): Promise<ApiTokenGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<ApiTokenGet>(this.buildPath(tokenId), { params: queryParams });
  }
}
