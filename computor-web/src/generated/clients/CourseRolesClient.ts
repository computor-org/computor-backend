/**
 * Auto-generated client for CourseRolesClient.
 * Endpoint: /course-roles
 */

import type { CourseRoleGet, CourseRoleList } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseRolesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-roles');
  }

  /**
   * List Course-Roles
   */
  async listCourseRolesCourseRolesGet({ description, id, limit, skip, title, userId }: { description?: string | null; id?: string | null; limit?: number | null; skip?: number | null; title?: string | null; userId?: string | null }): Promise<CourseRoleList[]> {
    const queryParams: Record<string, unknown> = {
      description,
      id,
      limit,
      skip,
      title,
      user_id: userId,
    };
    return this.client.get<CourseRoleList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Get Course-Roles
   */
  async getCourseRolesCourseRolesIdGet({ id, userId }: { id: string; userId?: string | null }): Promise<CourseRoleGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseRoleGet>(this.buildPath(id), { params: queryParams });
  }
}
