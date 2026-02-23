/**
 * Auto-generated client for CoursesClient.
 * Endpoint: /courses
 */

import type { CascadeDeleteResult, CourseCreate, CourseGet, CourseList, CourseUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CoursesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/courses');
  }

  /**
   * List Courses
   */
  async listCoursesCoursesGet({ courseFamilyId, description, fullPath, id, languageCode, limit, organizationId, path, providerUrl, skip, title, userId }: { courseFamilyId?: string | null; description?: string | null; fullPath?: string | null; id?: string | null; languageCode?: string | null; limit?: number | null; organizationId?: string | null; path?: string | null; providerUrl?: string | null; skip?: number | null; title?: string | null; userId?: string | null }): Promise<CourseList[]> {
    const queryParams: Record<string, unknown> = {
      course_family_id: courseFamilyId,
      description,
      full_path: fullPath,
      id,
      language_code: languageCode,
      limit,
      organization_id: organizationId,
      path,
      provider_url: providerUrl,
      skip,
      title,
      user_id: userId,
    };
    return this.client.get<CourseList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Courses
   */
  async createCoursesCoursesPost({ userId, body }: { userId?: string | null; body: CourseCreate }): Promise<CourseGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete course and all course-specific data
   * Delete a course and ALL its data including:
   * - All course members (NOT the users themselves)
   * - All course groups
   * - All course content types and contents
   * - All submission groups and their artifacts
   * - All results and grades
   * - All messages targeted to the course
   * **WARNING**: This is a destructive operation. Use dry_run=true to preview.
   */
  async deleteCourseEndpointCoursesCourseIdDelete({ courseId, dryRun, userId }: { courseId: string; dryRun?: boolean; userId?: string | null }): Promise<CascadeDeleteResult> {
    const queryParams: Record<string, unknown> = {
      dry_run: dryRun,
      user_id: userId,
    };
    return this.client.delete<CascadeDeleteResult>(this.buildPath(courseId), { params: queryParams });
  }

  /**
   * Delete Courses
   */
  async deleteCoursesCoursesIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Courses
   */
  async getCoursesCoursesIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<CourseGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Courses
   */
  async updateCoursesCoursesIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: CourseUpdate }): Promise<CourseGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<CourseGet>(this.buildPath(id), body, { params: queryParams });
  }
}
