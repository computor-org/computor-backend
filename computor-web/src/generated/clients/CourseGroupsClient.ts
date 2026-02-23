/**
 * Auto-generated client for CourseGroupsClient.
 * Endpoint: /course-groups
 */

import type { CourseGroupCreate, CourseGroupGet, CourseGroupList, CourseGroupUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseGroupsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-groups');
  }

  /**
   * List Course-Groups
   */
  async listCourseGroupsCourseGroupsGet({ courseId, id, limit, skip, title, userId }: { courseId?: string | null; id?: string | null; limit?: number | null; skip?: number | null; title?: string | null; userId?: string | null }): Promise<CourseGroupList[]> {
    const queryParams: Record<string, unknown> = {
      course_id: courseId,
      id,
      limit,
      skip,
      title,
      user_id: userId,
    };
    return this.client.get<CourseGroupList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Course-Groups
   */
  async createCourseGroupsCourseGroupsPost({ userId, body }: { userId?: string | null; body: CourseGroupCreate }): Promise<CourseGroupGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseGroupGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Course-Groups
   */
  async deleteCourseGroupsCourseGroupsIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Course-Groups
   */
  async getCourseGroupsCourseGroupsIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<CourseGroupGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseGroupGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Course-Groups
   */
  async updateCourseGroupsCourseGroupsIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: CourseGroupUpdate }): Promise<CourseGroupGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<CourseGroupGet>(this.buildPath(id), body, { params: queryParams });
  }
}
