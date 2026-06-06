/**
 * Auto-generated client for RoleClaimInterface.
 * Endpoint: /role-claims
 */

import type { RoleClaimGet, RoleClaimList, RoleClaimQuery } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class RoleClaimClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/role-claims');
  }

  async get(id: string | number): Promise<RoleClaimGet> {
    return this.client.get<RoleClaimGet>(this.buildPath(id));
  }

  async list(params?: RoleClaimQuery): Promise<RoleClaimList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<RoleClaimList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }
}
