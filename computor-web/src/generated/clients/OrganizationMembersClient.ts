/**
 * Auto-generated client for OrganizationMembersClient.
 * Endpoint: /organization-members
 */

import type { OrganizationMemberCreate, OrganizationMemberGet, OrganizationMemberList, OrganizationMemberUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class OrganizationMembersClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/organization-members');
  }

  /**
   * List Organization-Members
   */
  async listOrganizationMembersOrganizationMembersGet({ id, limit, organizationId, organizationRoleId, skip, userId }: { id?: string | null; limit?: number | null; organizationId?: string | null; organizationRoleId?: string | null; skip?: number | null; userId?: string | null }): Promise<OrganizationMemberList[]> {
    const queryParams: Record<string, unknown> = {
      id,
      limit,
      organization_id: organizationId,
      organization_role_id: organizationRoleId,
      skip,
      user_id: userId,
    };
    return this.client.get<OrganizationMemberList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Organization-Members
   */
  async createOrganizationMembersOrganizationMembersPost({ userId, body }: { userId?: string | null; body: OrganizationMemberCreate }): Promise<OrganizationMemberGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<OrganizationMemberGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Organization-Members
   */
  async deleteOrganizationMembersOrganizationMembersIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Organization-Members
   */
  async getOrganizationMembersOrganizationMembersIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<OrganizationMemberGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<OrganizationMemberGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Organization-Members
   */
  async updateOrganizationMembersOrganizationMembersIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: OrganizationMemberUpdate }): Promise<OrganizationMemberGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<OrganizationMemberGet>(this.buildPath(id), body, { params: queryParams });
  }
}
