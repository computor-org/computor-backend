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
   * Lecturer Get Courses
   */
  async lecturerGetCoursesLecturersCoursesCourseIdGet({ courseId }: { courseId: string | string }): Promise<CourseGet> {
    return this.client.get<CourseGet>(this.buildPath('courses', courseId));
  }

  /**
   * Lecturer List Courses
   */
  async lecturerListCoursesLecturersCoursesGet({ skip, limit, id, title, description, path, courseFamilyId, organizationId, providerUrl, fullPath }: { skip?: number | null; limit?: number | null; id?: string | null; title?: string | null; description?: string | null; path?: string | null; courseFamilyId?: string | null; organizationId?: string | null; providerUrl?: string | null; fullPath?: string | null }): Promise<CourseList[]> {
    const queryParams: Record<string, unknown> = {
      skip,
      limit,
      id,
      title,
      description,
      path,
      course_family_id: courseFamilyId,
      organization_id: organizationId,
      provider_url: providerUrl,
      full_path: fullPath,
    };
    return this.client.get<CourseList[]>(this.buildPath('courses'), { params: queryParams });
  }

  /**
   * Lecturer Get Course Contents
   * Get a specific course content with course repository information.
   */
  async lecturerGetCourseContentsLecturersCourseContentsCourseContentIdGet({ courseContentId }: { courseContentId: string | string }): Promise<CourseContentLecturerGet> {
    return this.client.get<CourseContentLecturerGet>(this.buildPath('course-contents', courseContentId));
  }

  /**
   * Lecturer List Course Contents
   * List course contents with course repository information.
   */
  async lecturerListCourseContentsLecturersCourseContentsGet({ skip, limit, id, title, path, courseId, courseContentTypeId, archived, position, maxGroupSize, maxTestRuns, maxSubmissions, executionBackendId, hasDeployment }: { skip?: number | null; limit?: number | null; id?: string | null; title?: string | null; path?: string | null; courseId?: string | null; courseContentTypeId?: string | null; archived?: boolean | null; position?: number | null; maxGroupSize?: number | null; maxTestRuns?: number | null; maxSubmissions?: number | null; executionBackendId?: string | null; hasDeployment?: boolean | null }): Promise<CourseContentLecturerList[]> {
    const queryParams: Record<string, unknown> = {
      skip,
      limit,
      id,
      title,
      path,
      course_id: courseId,
      course_content_type_id: courseContentTypeId,
      archived,
      position,
      max_group_size: maxGroupSize,
      max_test_runs: maxTestRuns,
      max_submissions: maxSubmissions,
      execution_backend_id: executionBackendId,
      has_deployment: hasDeployment,
    };
    return this.client.get<CourseContentLecturerList[]>(this.buildPath('course-contents'), { params: queryParams });
  }
}
