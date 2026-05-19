/**
 * Client for GET /role-claims
 * Role claims are read-only (list only — no create/update/delete endpoint).
 */

import type { RoleClaimList } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class RoleClaimsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/role-claims');
  }

  async listClaims({ roleId, claimType, claimValue, limit, skip }: {
    roleId?: string;
    claimType?: string;
    claimValue?: string;
    limit?: number;
    skip?: number;
  } = {}): Promise<RoleClaimList[]> {
    return this.client.get<RoleClaimList[]>(this.basePath, {
      params: { role_id: roleId, claim_type: claimType, claim_value: claimValue, limit, skip },
    });
  }
}
