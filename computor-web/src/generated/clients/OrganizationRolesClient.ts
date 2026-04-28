/**
 * Auto-generated client for OrganizationRolesClient.
 * Endpoint: /organization-roles
 */

import type { OrganizationRoleGet, OrganizationRoleList } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class OrganizationRolesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/organization-roles');
  }

  /**
   * List Organization-Roles
   */
  async listOrganizationRolesOrganizationRolesGet({ builtin, description, id, limit, skip, title, userId }: { builtin?: boolean | null; description?: string | null; id?: string | null; limit?: number | null; skip?: number | null; title?: string | null; userId?: string | null }): Promise<OrganizationRoleList[]> {
    const queryParams: Record<string, unknown> = {
      builtin,
      description,
      id,
      limit,
      skip,
      title,
      user_id: userId,
    };
    return this.client.get<OrganizationRoleList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Get Organization-Roles
   */
  async getOrganizationRolesOrganizationRolesIdGet({ id, userId }: { id: string; userId?: string | null }): Promise<OrganizationRoleGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<OrganizationRoleGet>(this.buildPath(id), { params: queryParams });
  }
}
