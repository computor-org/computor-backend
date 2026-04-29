/**
 * Auto-generated client for CourseFamilyMembersClient.
 * Endpoint: /course-family-members
 */

import type { CourseFamilyMemberCreate, CourseFamilyMemberGet, CourseFamilyMemberList, CourseFamilyMemberUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseFamilyMembersClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-family-members');
  }

  /**
   * List Course-Family-Members
   */
  async listCourseFamilyMembersCourseFamilyMembersGet({ courseFamilyId, courseFamilyRoleId, id, limit, skip, userId }: { courseFamilyId?: string | null; courseFamilyRoleId?: string | null; id?: string | null; limit?: number | null; skip?: number | null; userId?: string | null }): Promise<CourseFamilyMemberList[]> {
    const queryParams: Record<string, unknown> = {
      course_family_id: courseFamilyId,
      course_family_role_id: courseFamilyRoleId,
      id,
      limit,
      skip,
      user_id: userId,
    };
    return this.client.get<CourseFamilyMemberList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Course-Family-Members
   */
  async createCourseFamilyMembersCourseFamilyMembersPost({ userId, body }: { userId?: string | null; body: CourseFamilyMemberCreate }): Promise<CourseFamilyMemberGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseFamilyMemberGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Course-Family-Members
   */
  async deleteCourseFamilyMembersCourseFamilyMembersIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Course-Family-Members
   */
  async getCourseFamilyMembersCourseFamilyMembersIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<CourseFamilyMemberGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseFamilyMemberGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Course-Family-Members
   */
  async updateCourseFamilyMembersCourseFamilyMembersIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: CourseFamilyMemberUpdate }): Promise<CourseFamilyMemberGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<CourseFamilyMemberGet>(this.buildPath(id), body, { params: queryParams });
  }
}
