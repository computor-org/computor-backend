/**
 * Auto-generated client for GitServersClient.
 * Endpoint: /git-servers
 */

import type { GitServerCreate, GitServerGet, GitServerUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class GitServersClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/git-servers');
  }

  /**
   * List Git Servers Endpoint
   */
  async listGitServersEndpointGitServersGet({ userId }: { userId?: string | null }): Promise<GitServerGet[]> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<GitServerGet[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Git Server Endpoint
   * Register a git server instance (the service token is stored encrypted).
   */
  async createGitServerEndpointGitServersPost({ userId, body }: { userId?: string | null; body: GitServerCreate }): Promise<GitServerGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<GitServerGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Git Server Endpoint
   */
  async deleteGitServerEndpointGitServersServerIdDelete({ serverId, userId }: { serverId: string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(serverId), { params: queryParams });
  }

  /**
   * Get Git Server Endpoint
   */
  async getGitServerEndpointGitServersServerIdGet({ serverId, userId }: { serverId: string; userId?: string | null }): Promise<GitServerGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<GitServerGet>(this.buildPath(serverId), { params: queryParams });
  }

  /**
   * Update Git Server Endpoint
   */
  async updateGitServerEndpointGitServersServerIdPatch({ serverId, userId, body }: { serverId: string; userId?: string | null; body: GitServerUpdate }): Promise<GitServerGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<GitServerGet>(this.buildPath(serverId), body, { params: queryParams });
  }
}
