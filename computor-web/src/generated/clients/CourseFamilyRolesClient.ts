/**
 * Auto-generated client for CourseFamilyRolesClient.
 * Endpoint: /course-family-roles
 */

import type { CourseFamilyRoleGet, CourseFamilyRoleList } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseFamilyRolesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-family-roles');
  }

  /**
   * List Course-Family-Roles
   */
  async listCourseFamilyRolesCourseFamilyRolesGet({ builtin, description, id, limit, skip, title, userId }: { builtin?: boolean | null; description?: string | null; id?: string | null; limit?: number | null; skip?: number | null; title?: string | null; userId?: string | null }): Promise<CourseFamilyRoleList[]> {
    const queryParams: Record<string, unknown> = {
      builtin,
      description,
      id,
      limit,
      skip,
      title,
      user_id: userId,
    };
    return this.client.get<CourseFamilyRoleList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Get Course-Family-Roles
   */
  async getCourseFamilyRolesCourseFamilyRolesIdGet({ id, userId }: { id: string; userId?: string | null }): Promise<CourseFamilyRoleGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseFamilyRoleGet>(this.buildPath(id), { params: queryParams });
  }
}
