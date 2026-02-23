/**
 * Auto-generated client for ExampleRepositoriesClient.
 * Endpoint: /example-repositories
 */

import type { ExampleRepositoryCreate, ExampleRepositoryGet, ExampleRepositoryList, ExampleRepositoryUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ExampleRepositoriesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/example-repositories');
  }

  /**
   * List Example-Repositories
   */
  async listExampleRepositoriesExampleRepositoriesGet({ id, limit, name, organizationId, skip, sourceType, userId }: { id?: string | null; limit?: number | null; name?: string | null; organizationId?: string | null; skip?: number | null; sourceType?: string | null; userId?: string | null }): Promise<ExampleRepositoryList[]> {
    const queryParams: Record<string, unknown> = {
      id,
      limit,
      name,
      organization_id: organizationId,
      skip,
      source_type: sourceType,
      user_id: userId,
    };
    return this.client.get<ExampleRepositoryList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Example-Repositories
   */
  async createExampleRepositoriesExampleRepositoriesPost({ userId, body }: { userId?: string | null; body: ExampleRepositoryCreate }): Promise<ExampleRepositoryGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<ExampleRepositoryGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Example-Repositories
   */
  async deleteExampleRepositoriesExampleRepositoriesIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Example-Repositories
   */
  async getExampleRepositoriesExampleRepositoriesIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<ExampleRepositoryGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<ExampleRepositoryGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Example-Repositories
   */
  async updateExampleRepositoriesExampleRepositoriesIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: ExampleRepositoryUpdate }): Promise<ExampleRepositoryGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<ExampleRepositoryGet>(this.buildPath(id), body, { params: queryParams });
  }
}
