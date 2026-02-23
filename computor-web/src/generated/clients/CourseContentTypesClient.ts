/**
 * Auto-generated client for CourseContentTypesClient.
 * Endpoint: /course-content-types
 */

import type { CourseContentTypeCreate, CourseContentTypeGet, CourseContentTypeList, CourseContentTypeUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseContentTypesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-content-types');
  }

  /**
   * List Course-Content-Types
   */
  async listCourseContentTypesCourseContentTypesGet({ color, courseContentKindId, courseId, description, id, limit, skip, slug, title, userId }: { color?: string | null; courseContentKindId?: string | null; courseId?: string | null; description?: string | null; id?: string | null; limit?: number | null; skip?: number | null; slug?: string | null; title?: string | null; userId?: string | null }): Promise<CourseContentTypeList[]> {
    const queryParams: Record<string, unknown> = {
      color,
      course_content_kind_id: courseContentKindId,
      course_id: courseId,
      description,
      id,
      limit,
      skip,
      slug,
      title,
      user_id: userId,
    };
    return this.client.get<CourseContentTypeList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Course-Content-Types
   */
  async createCourseContentTypesCourseContentTypesPost({ userId, body }: { userId?: string | null; body: CourseContentTypeCreate }): Promise<CourseContentTypeGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseContentTypeGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Course-Content-Types
   */
  async deleteCourseContentTypesCourseContentTypesIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Course-Content-Types
   */
  async getCourseContentTypesCourseContentTypesIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<CourseContentTypeGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseContentTypeGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Course-Content-Types
   */
  async updateCourseContentTypesCourseContentTypesIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: CourseContentTypeUpdate }): Promise<CourseContentTypeGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<CourseContentTypeGet>(this.buildPath(id), body, { params: queryParams });
  }
}
