/**
 * Auto-generated client for CourseInterface.
 * Endpoint: /courses
 */

import type { CourseCreate, CourseExecutionBackendGet, CourseGet, CourseList, CourseQuery, CourseUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/courses');
  }

  async create(payload: CourseCreate): Promise<CourseGet> {
    return this.client.post<CourseGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<CourseGet> {
    return this.client.get<CourseGet>(this.buildPath(id));
  }

  async list(params?: CourseQuery): Promise<CourseList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<CourseList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: CourseUpdate): Promise<CourseGet> {
    return this.client.patch<CourseGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }

  /**
   * Patch Course Execution Backend
   */
  async patchCourseExecutionBackendCoursesCourseIdExecutionBackendsExecutionBackendIdPatch({ courseId, executionBackendId, body }: { courseId: string | string; executionBackendId: string | string; body: Record<string, unknown> & Record<string, unknown> }): Promise<CourseExecutionBackendGet> {
    return this.client.patch<CourseExecutionBackendGet>(this.buildPath(courseId, 'execution-backends', executionBackendId), body);
  }

  /**
   * Delete Course Execution Backend
   */
  async deleteCourseExecutionBackendCoursesCourseIdExecutionBackendsExecutionBackendIdDelete({ courseId, executionBackendId }: { courseId: string | string; executionBackendId: string | string }): Promise<Record<string, unknown> & Record<string, unknown>> {
    return this.client.delete<Record<string, unknown> & Record<string, unknown>>(this.buildPath(courseId, 'execution-backends', executionBackendId));
  }
}
