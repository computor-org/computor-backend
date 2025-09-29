/**
 * Auto-generated client for CourseContentLecturerInterface.
 * Endpoint: /lecturer-course-contents
 */

import type { CourseContentLecturerGet, CourseContentLecturerList, CourseContentLecturerQuery } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseContentLecturerClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/lecturer-course-contents');
  }

  async get(id: string | number): Promise<CourseContentLecturerGet> {
    return this.client.get<CourseContentLecturerGet>(this.buildPath(id));
  }

  async list(params?: CourseContentLecturerQuery): Promise<CourseContentLecturerList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<CourseContentLecturerList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }
}
