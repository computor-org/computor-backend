/**
 * Auto-generated client for CourseContentInterface.
 * Endpoint: /course-contents
 */

import type { CourseContentCreate, CourseContentGet, CourseContentList, CourseContentQuery, CourseContentUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseContentClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-contents');
  }

  async create(payload: CourseContentCreate): Promise<CourseContentGet> {
    return this.client.post<CourseContentGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<CourseContentGet> {
    return this.client.get<CourseContentGet>(this.buildPath(id));
  }

  async list(params?: CourseContentQuery): Promise<CourseContentList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<CourseContentList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: CourseContentUpdate): Promise<CourseContentGet> {
    return this.client.patch<CourseContentGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }

  async archive(id: string | number): Promise<void> {
    await this.client.patch<void>(this.buildPath(id, 'archive'));
  }
}
