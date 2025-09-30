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
   * Student Get Course Content
   */
  async studentGetCourseContentStudentsCourseContentsCourseContentIdGet({ courseContentId }: { courseContentId: string | string }): Promise<CourseContentStudentGet> {
    return this.client.get<CourseContentStudentGet>(this.buildPath('course-contents', courseContentId));
  }

  /**
   * Student List Course Contents
   */
  async studentListCourseContentsStudentsCourseContentsGet({ skip, limit, id, title, path, courseId, courseContentTypeId, directory, project, providerUrl, nlevel, descendants, ascendants }: { skip?: number | null; limit?: number | null; id?: string | null; title?: string | null; path?: string | null; courseId?: string | null; courseContentTypeId?: string | null; directory?: string | null; project?: string | null; providerUrl?: string | null; nlevel?: number | null; descendants?: string | null; ascendants?: string | null }): Promise<CourseContentStudentList[]> {
    const queryParams: Record<string, unknown> = {
      skip,
      limit,
      id,
      title,
      path,
      course_id: courseId,
      course_content_type_id: courseContentTypeId,
      directory,
      project,
      provider_url: providerUrl,
      nlevel,
      descendants,
      ascendants,
    };
    return this.client.get<CourseContentStudentList[]>(this.buildPath('course-contents'), { params: queryParams });
  }

  /**
   * Student List Courses
   */
  async studentListCoursesStudentsCoursesGet({ skip, limit, id, title, description, path, courseFamilyId, organizationId, providerUrl, fullPath, fullPathStudent }: { skip?: number | null; limit?: number | null; id?: string | null; title?: string | null; description?: string | null; path?: string | null; courseFamilyId?: string | null; organizationId?: string | null; providerUrl?: string | null; fullPath?: string | null; fullPathStudent?: string | null }): Promise<CourseStudentList[]> {
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
      full_path_student: fullPathStudent,
    };
    return this.client.get<CourseStudentList[]>(this.buildPath('courses'), { params: queryParams });
  }

  /**
   * Student Get Course
   */
  async studentGetCourseStudentsCoursesCourseIdGet({ courseId }: { courseId: string | string }): Promise<CourseStudentGet> {
    return this.client.get<CourseStudentGet>(this.buildPath('courses', courseId));
  }

  /**
   * Get Signup Init Data
   */
  async getSignupInitDataStudentsRepositoriesGet(): Promise<string[]> {
    return this.client.get<string[]>(this.buildPath('repositories'));
  }
}
