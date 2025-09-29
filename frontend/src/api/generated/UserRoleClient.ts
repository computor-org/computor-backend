/**
 * Auto-generated client for UserRoleInterface.
 * Endpoint: /user-roles
 */

import type { UserRoleCreate, UserRoleGet, UserRoleList, UserRoleQuery, UserRoleUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class UserRoleClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/user-roles');
  }

  async create(payload: UserRoleCreate): Promise<UserRoleGet> {
    return this.client.post<UserRoleGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<UserRoleGet> {
    return this.client.get<UserRoleGet>(this.buildPath(id));
  }

  async list(params?: UserRoleQuery): Promise<UserRoleList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<UserRoleList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: UserRoleUpdate): Promise<UserRoleGet> {
    return this.client.patch<UserRoleGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }
}
