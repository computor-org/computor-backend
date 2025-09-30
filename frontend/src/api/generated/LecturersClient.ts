/**
 * Auto-generated client for LecturersClient.
 * Endpoint: /lecturers
 */

import type { CourseContentLecturerGet, CourseContentLecturerList, CourseGet, CourseList } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class LecturersClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/lecturers');
  }

  /**
   * Lecturer List Course Contents
   * List course contents with course repository information.
   */
  async lecturerListCourseContentsLecturersCourseContentsGet({ archived, courseContentTypeId, courseId, executionBackendId, hasDeployment, id, limit, maxGroupSize, maxSubmissions, maxTestRuns, path, position, skip, title }: { archived?: boolean | null; courseContentTypeId?: string | null; courseId?: string | null; executionBackendId?: string | null; hasDeployment?: boolean | null; id?: string | null; limit?: number | null; maxGroupSize?: number | null; maxSubmissions?: number | null; maxTestRuns?: number | null; path?: string | null; position?: number | null; skip?: number | null; title?: string | null }): Promise<CourseContentLecturerList[]> {
    const queryParams: Record<string, unknown> = {
      archived,
      course_content_type_id: courseContentTypeId,
      course_id: courseId,
      execution_backend_id: executionBackendId,
      has_deployment: hasDeployment,
      id,
      limit,
      max_group_size: maxGroupSize,
      max_submissions: maxSubmissions,
      max_test_runs: maxTestRuns,
      path,
      position,
      skip,
      title,
    };
    return this.client.get<CourseContentLecturerList[]>(this.buildPath('course-contents'), { params: queryParams });
  }

  /**
   * Lecturer Get Course Contents
   * Get a specific course content with course repository information.
   */
  async lecturerGetCourseContentsLecturersCourseContentsCourseContentIdGet({ courseContentId }: { courseContentId: string | string }): Promise<CourseContentLecturerGet> {
    return this.client.get<CourseContentLecturerGet>(this.buildPath('course-contents', courseContentId));
  }

  /**
   * Lecturer List Courses
   */
  async lecturerListCoursesLecturersCoursesGet({ courseFamilyId, description, fullPath, id, limit, organizationId, path, providerUrl, skip, title }: { courseFamilyId?: string | null; description?: string | null; fullPath?: string | null; id?: string | null; limit?: number | null; organizationId?: string | null; path?: string | null; providerUrl?: string | null; skip?: number | null; title?: string | null }): Promise<CourseList[]> {
    const queryParams: Record<string, unknown> = {
      course_family_id: courseFamilyId,
      description,
      full_path: fullPath,
      id,
      limit,
      organization_id: organizationId,
      path,
      provider_url: providerUrl,
      skip,
      title,
    };
    return this.client.get<CourseList[]>(this.buildPath('courses'), { params: queryParams });
  }

  /**
   * Lecturer Get Courses
   */
  async lecturerGetCoursesLecturersCoursesCourseIdGet({ courseId }: { courseId: string | string }): Promise<CourseGet> {
    return this.client.get<CourseGet>(this.buildPath('courses', courseId));
  }
}
