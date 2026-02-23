/**
 * Auto-generated client for CourseMembersClient.
 * Endpoint: /course-members
 */

import type { CourseMemberCreate, CourseMemberGet, CourseMemberList, CourseMemberUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseMembersClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-members');
  }

  /**
   * List Course-Members
   */
  async listCourseMembersCourseMembersGet({ courseGroupId, courseId, courseRoleId, familyName, givenName, id, limit, skip, userId }: { courseGroupId?: string | null; courseId?: string | null; courseRoleId?: string | null; familyName?: string | null; givenName?: string | null; id?: string | null; limit?: number | null; skip?: number | null; userId?: string | null }): Promise<CourseMemberList[]> {
    const queryParams: Record<string, unknown> = {
      course_group_id: courseGroupId,
      course_id: courseId,
      course_role_id: courseRoleId,
      family_name: familyName,
      given_name: givenName,
      id,
      limit,
      skip,
      user_id: userId,
    };
    return this.client.get<CourseMemberList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Course-Members
   */
  async createCourseMembersCourseMembersPost({ userId, body }: { userId?: string | null; body: CourseMemberCreate }): Promise<CourseMemberGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseMemberGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Course-Members
   */
  async deleteCourseMembersCourseMembersIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Course-Members
   */
  async getCourseMembersCourseMembersIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<CourseMemberGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseMemberGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Course-Members
   */
  async updateCourseMembersCourseMembersIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: CourseMemberUpdate }): Promise<CourseMemberGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<CourseMemberGet>(this.buildPath(id), body, { params: queryParams });
  }
}
