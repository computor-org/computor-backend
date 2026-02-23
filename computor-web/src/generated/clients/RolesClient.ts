/**
 * Auto-generated client for RolesClient.
 * Endpoint: /roles
 */

import type { RoleGet, RoleList } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class RolesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/roles');
  }

  /**
   * List Roles
   */
  async listRolesRolesGet({ builtin, description, id, limit, skip, title, userId }: { builtin?: boolean | null; description?: string | null; id?: string | null; limit?: number | null; skip?: number | null; title?: string | null; userId?: string | null }): Promise<RoleList[]> {
    const queryParams: Record<string, unknown> = {
      builtin,
      description,
      id,
      limit,
      skip,
      title,
      user_id: userId,
    };
    return this.client.get<RoleList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Get Roles
   */
  async getRolesRolesIdGet({ id, userId }: { id: string; userId?: string | null }): Promise<RoleGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<RoleGet>(this.buildPath(id), { params: queryParams });
  }
}
