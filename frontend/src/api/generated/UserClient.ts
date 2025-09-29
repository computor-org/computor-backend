/**
 * Auto-generated client for UserInterface.
 * Endpoint: /users
 */

import type { UserCreate, UserGet, UserList, UserQuery, UserUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class UserClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/users');
  }

  async create(payload: UserCreate): Promise<UserGet> {
    return this.client.post<UserGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<UserGet> {
    return this.client.get<UserGet>(this.buildPath(id));
  }

  async list(params?: UserQuery): Promise<UserList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<UserList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: UserUpdate): Promise<UserGet> {
    return this.client.patch<UserGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }

  async archive(id: string | number): Promise<void> {
    await this.client.patch<void>(this.buildPath(id, 'archive'));
  }
}
