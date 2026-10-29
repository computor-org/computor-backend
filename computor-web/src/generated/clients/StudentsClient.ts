/**
 * Auto-generated client for StudentsClient.
 * Endpoint: /students
 */

import type { CourseContentStudentGet, CourseContentStudentList, CourseStudentGet, CourseStudentList } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class StudentsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/students');
  }

  /**
   * Student List Course Contents Endpoint
   */
  async studentListCourseContentsEndpointStudentsCourseContentsGet({ ascendants, courseContentTypeId, courseId, descendants, directory, id, limit, localize, nlevel, path, project, providerUrl, skip, status, title }: { ascendants?: string | null; courseContentTypeId?: string | null; courseId?: string | null; descendants?: string | null; directory?: string | null; id?: string | null; limit?: number | null; localize?: string | null; nlevel?: number | null; path?: string | null; project?: string | null; providerUrl?: string | null; skip?: number | null; status?: string | null; title?: string | null }): Promise<CourseContentStudentList[]> {
    const queryParams: Record<string, unknown> = {
      ascendants,
      course_content_type_id: courseContentTypeId,
      course_id: courseId,
      descendants,
      directory,
      id,
      limit,
      localize,
      nlevel,
      path,
      project,
      provider_url: providerUrl,
      skip,
      status,
      title,
    };
    return this.client.get<CourseContentStudentList[]>(this.buildPath('course-contents'), { params: queryParams });
  }

  /**
   * Student Get Course Content Endpoint
   */
  async studentGetCourseContentEndpointStudentsCourseContentsCourseContentIdGet({ courseContentId, localize }: { courseContentId: string | string; localize?: string | null }): Promise<CourseContentStudentGet> {
    const queryParams: Record<string, unknown> = {
      localize,
    };
    return this.client.get<CourseContentStudentGet>(this.buildPath('course-contents', courseContentId), { params: queryParams });
  }

  /**
   * Student List Courses Endpoint
   */
  async studentListCoursesEndpointStudentsCoursesGet({ courseFamilyId, description, id, limit, localize, organizationId, path, skip, title }: { courseFamilyId?: string | null; description?: string | null; id?: string | null; limit?: number | null; localize?: string | null; organizationId?: string | null; path?: string | null; skip?: number | null; title?: string | null }): Promise<CourseStudentList[]> {
    const queryParams: Record<string, unknown> = {
      course_family_id: courseFamilyId,
      description,
      id,
      limit,
      localize,
      organization_id: organizationId,
      path,
      skip,
      title,
    };
    return this.client.get<CourseStudentList[]>(this.buildPath('courses'), { params: queryParams });
  }

  /**
   * Student Get Course Endpoint
   */
  async studentGetCourseEndpointStudentsCoursesCourseIdGet({ courseId, localize }: { courseId: string | string; localize?: string | null }): Promise<CourseStudentGet> {
    const queryParams: Record<string, unknown> = {
      localize,
    };
    return this.client.get<CourseStudentGet>(this.buildPath('courses', courseId), { params: queryParams });
  }
}
