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
  async studentListCourseContentsEndpointStudentsCourseContentsGet({ ascendants, courseContentTypeId, courseId, descendants, directory, id, limit, nlevel, path, project, providerUrl, skip, title }: { ascendants?: string | null; courseContentTypeId?: string | null; courseId?: string | null; descendants?: string | null; directory?: string | null; id?: string | null; limit?: number | null; nlevel?: number | null; path?: string | null; project?: string | null; providerUrl?: string | null; skip?: number | null; title?: string | null }): Promise<CourseContentStudentList[]> {
    const queryParams: Record<string, unknown> = {
      ascendants,
      course_content_type_id: courseContentTypeId,
      course_id: courseId,
      descendants,
      directory,
      id,
      limit,
      nlevel,
      path,
      project,
      provider_url: providerUrl,
      skip,
      title,
    };
    return this.client.get<CourseContentStudentList[]>(this.buildPath('course-contents'), { params: queryParams });
  }

  /**
   * Student Get Course Content Endpoint
   */
  async studentGetCourseContentEndpointStudentsCourseContentsCourseContentIdGet({ courseContentId }: { courseContentId: string | string }): Promise<CourseContentStudentGet> {
    return this.client.get<CourseContentStudentGet>(this.buildPath('course-contents', courseContentId));
  }

  /**
   * Student List Courses Endpoint
   */
  async studentListCoursesEndpointStudentsCoursesGet({ courseFamilyId, description, fullPath, fullPathStudent, id, limit, organizationId, path, providerUrl, skip, title }: { courseFamilyId?: string | null; description?: string | null; fullPath?: string | null; fullPathStudent?: string | null; id?: string | null; limit?: number | null; organizationId?: string | null; path?: string | null; providerUrl?: string | null; skip?: number | null; title?: string | null }): Promise<CourseStudentList[]> {
    const queryParams: Record<string, unknown> = {
      course_family_id: courseFamilyId,
      description,
      full_path: fullPath,
      full_path_student: fullPathStudent,
      id,
      limit,
      organization_id: organizationId,
      path,
      provider_url: providerUrl,
      skip,
      title,
    };
    return this.client.get<CourseStudentList[]>(this.buildPath('courses'), { params: queryParams });
  }

  /**
   * Student Get Course Endpoint
   */
  async studentGetCourseEndpointStudentsCoursesCourseIdGet({ courseId }: { courseId: string | string }): Promise<CourseStudentGet> {
    return this.client.get<CourseStudentGet>(this.buildPath('courses', courseId));
  }
}
