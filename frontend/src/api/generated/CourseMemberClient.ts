/**
 * Auto-generated client for CourseMemberInterface.
 * Endpoint: /course-members
 */

import type { CourseMemberCreate, CourseMemberGet, CourseMemberList, CourseMemberQuery, CourseMemberUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseMemberClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-members');
  }

  async create(payload: CourseMemberCreate): Promise<CourseMemberGet> {
    return this.client.post<CourseMemberGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<CourseMemberGet> {
    return this.client.get<CourseMemberGet>(this.buildPath(id));
  }

  async list(params?: CourseMemberQuery): Promise<CourseMemberList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<CourseMemberList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: CourseMemberUpdate): Promise<CourseMemberGet> {
    return this.client.patch<CourseMemberGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }
}
