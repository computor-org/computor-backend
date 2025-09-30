/**
 * Auto-generated client for OrganizationInterface.
 * Endpoint: /organizations
 */

import type { OrganizationCreate, OrganizationGet, OrganizationList, OrganizationQuery, OrganizationUpdate, OrganizationUpdateTokenUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class OrganizationClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/organizations');
  }

  async create(payload: OrganizationCreate): Promise<OrganizationGet> {
    return this.client.post<OrganizationGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<OrganizationGet> {
    return this.client.get<OrganizationGet>(this.buildPath(id));
  }

  async list(params?: OrganizationQuery): Promise<OrganizationList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<OrganizationList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: OrganizationUpdate): Promise<OrganizationGet> {
    return this.client.patch<OrganizationGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }

  async archive(id: string | number): Promise<void> {
    await this.client.patch<void>(this.buildPath(id, 'archive'));
  }

  /**
   * Patch Organizations Token
   */
  async patchOrganizationsTokenOrganizationsOrganizationIdTokenPatch({ organizationId, type, body }: { organizationId: string | string; type: string; body: OrganizationUpdateTokenUpdate }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      type,
    };
    return this.client.patch<void>(this.buildPath(organizationId, 'token'), body, { params: queryParams });
  }

  /**
   * Route Organizations
   */
  async routeOrganizationsOrganizationsIdArchivePatch({ id }: { id: string | string }): Promise<void> {
    return this.client.patch<void>(this.buildPath(id, 'archive'));
  }
}
