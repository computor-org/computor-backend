/**
 * Auto-generated client for CourseContentKindsClient.
 * Endpoint: /course-content-kinds
 */

import type { CourseContentKindCreate, CourseContentKindGet, CourseContentKindList, CourseContentKindUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseContentKindsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-content-kinds');
  }

  /**
   * List Course-Content-Kinds
   */
  async listCourseContentKindsCourseContentKindsGet({ description, hasAscendants, hasDescendants, id, limit, skip, submittable, title, userId }: { description?: string | null; hasAscendants?: boolean | null; hasDescendants?: boolean | null; id?: string | null; limit?: number | null; skip?: number | null; submittable?: boolean | null; title?: string | null; userId?: string | null }): Promise<CourseContentKindList[]> {
    const queryParams: Record<string, unknown> = {
      description,
      has_ascendants: hasAscendants,
      has_descendants: hasDescendants,
      id,
      limit,
      skip,
      submittable,
      title,
      user_id: userId,
    };
    return this.client.get<CourseContentKindList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Course-Content-Kinds
   */
  async createCourseContentKindsCourseContentKindsPost({ userId, body }: { userId?: string | null; body: CourseContentKindCreate }): Promise<CourseContentKindGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseContentKindGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Course-Content-Kinds
   */
  async deleteCourseContentKindsCourseContentKindsIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Course-Content-Kinds
   */
  async getCourseContentKindsCourseContentKindsIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<CourseContentKindGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseContentKindGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Course-Content-Kinds
   */
  async updateCourseContentKindsCourseContentKindsIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: CourseContentKindUpdate }): Promise<CourseContentKindGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<CourseContentKindGet>(this.buildPath(id), body, { params: queryParams });
  }
}
