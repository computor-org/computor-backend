/**
 * Auto-generated client for CourseFamiliesClient.
 * Endpoint: /course-families
 */

import type { CascadeDeleteResult, CourseFamilyCreate, CourseFamilyGet, CourseFamilyList, CourseFamilyUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseFamiliesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-families');
  }

  /**
   * List Course-Families
   */
  async listCourseFamiliesCourseFamiliesGet({ description, id, limit, organizationId, path, skip, title, userId }: { description?: string | null; id?: string | null; limit?: number | null; organizationId?: string | null; path?: string | null; skip?: number | null; title?: string | null; userId?: string | null }): Promise<CourseFamilyList[]> {
    const queryParams: Record<string, unknown> = {
      description,
      id,
      limit,
      organization_id: organizationId,
      path,
      skip,
      title,
      user_id: userId,
    };
    return this.client.get<CourseFamilyList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Course-Families
   */
  async createCourseFamiliesCourseFamiliesPost({ userId, body }: { userId?: string | null; body: CourseFamilyCreate }): Promise<CourseFamilyGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseFamilyGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete course family and all descendant courses
   * Delete a course family and ALL its descendant data including:
   * - All courses in the family
   * - All course members, groups, contents, submissions
   * - All messages targeted to the family or its courses
   * **WARNING**: This is a destructive operation. Use dry_run=true to preview.
   */
  async deleteCourseFamilyEndpointCourseFamiliesCourseFamilyIdDelete({ courseFamilyId, dryRun, userId }: { courseFamilyId: string; dryRun?: boolean; userId?: string | null }): Promise<CascadeDeleteResult> {
    const queryParams: Record<string, unknown> = {
      dry_run: dryRun,
      user_id: userId,
    };
    return this.client.delete<CascadeDeleteResult>(this.buildPath(courseFamilyId), { params: queryParams });
  }

  /**
   * Delete Course-Families
   */
  async deleteCourseFamiliesCourseFamiliesIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Course-Families
   */
  async getCourseFamiliesCourseFamiliesIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<CourseFamilyGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseFamilyGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Course-Families
   */
  async updateCourseFamiliesCourseFamiliesIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: CourseFamilyUpdate }): Promise<CourseFamilyGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<CourseFamilyGet>(this.buildPath(id), body, { params: queryParams });
  }
}
