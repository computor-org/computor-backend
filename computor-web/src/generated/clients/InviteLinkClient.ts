/**
 * Auto-generated client for InviteLinkInterface.
 * Endpoint: /admin/invites
 */

import type { InviteLinkCreate, InviteLinkGet, InviteLinkList } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class InviteLinkClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/admin/invites');
  }

  async create(payload: InviteLinkCreate): Promise<InviteLinkGet> {
    return this.client.post<InviteLinkGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<InviteLinkGet> {
    return this.client.get<InviteLinkGet>(this.buildPath(id));
  }

  async list(params?: Record<string, unknown>): Promise<InviteLinkList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<InviteLinkList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }
}
