/**
 * Auto-generated client for TutorsClient.
 * Endpoint: /tutors
 */

import type { CourseContentStudentGet, CourseContentStudentList, CourseMemberProperties, CourseTutorGet, CourseTutorList, TutorCourseMemberGet, TutorCourseMemberList, TutorGradeCreate, TutorGradeResponse } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class TutorsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/tutors');
  }

  /**
   * Tutor List Course Members
   */
  async tutorListCourseMembersTutorsCourseMembersGet({ courseGroupId, courseId, courseRoleId, familyName, givenName, id, limit, skip, userId }: { courseGroupId?: string | null; courseId?: string | null; courseRoleId?: string | null; familyName?: string | null; givenName?: string | null; id?: string | null; limit?: number | null; skip?: number | null; userId?: string | null }): Promise<TutorCourseMemberList[]> {
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
    return this.client.get<TutorCourseMemberList[]>(this.buildPath('course-members'), { params: queryParams });
  }

  /**
   * Tutor Get Course Members
   */
  async tutorGetCourseMembersTutorsCourseMembersCourseMemberIdGet({ courseMemberId }: { courseMemberId: string | string }): Promise<TutorCourseMemberGet> {
    return this.client.get<TutorCourseMemberGet>(this.buildPath('course-members', courseMemberId));
  }

  /**
   * Tutor List Course Contents
   */
  async tutorListCourseContentsTutorsCourseMembersCourseMemberIdCourseContentsGet({ courseMemberId, ascendants, courseContentTypeId, courseId, descendants, directory, id, limit, nlevel, path, project, providerUrl, skip, title }: { courseMemberId: string | string; ascendants?: string | null; courseContentTypeId?: string | null; courseId?: string | null; descendants?: string | null; directory?: string | null; id?: string | null; limit?: number | null; nlevel?: number | null; path?: string | null; project?: string | null; providerUrl?: string | null; skip?: number | null; title?: string | null }): Promise<CourseContentStudentList[]> {
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
    return this.client.get<CourseContentStudentList[]>(this.buildPath('course-members', courseMemberId, 'course-contents'), { params: queryParams });
  }

  /**
   * Tutor Get Course Contents
   */
  async tutorGetCourseContentsTutorsCourseMembersCourseMemberIdCourseContentsCourseContentIdGet({ courseContentId, courseMemberId }: { courseContentId: string | string; courseMemberId: string | string }): Promise<CourseContentStudentGet> {
    return this.client.get<CourseContentStudentGet>(this.buildPath('course-members', courseMemberId, 'course-contents', courseContentId));
  }

  /**
   * Tutor Update Course Contents
   */
  async tutorUpdateCourseContentsTutorsCourseMembersCourseMemberIdCourseContentsCourseContentIdPatch({ courseContentId, courseMemberId, body }: { courseContentId: string | string; courseMemberId: string | string; body: TutorGradeCreate }): Promise<TutorGradeResponse> {
    return this.client.patch<TutorGradeResponse>(this.buildPath('course-members', courseMemberId, 'course-contents', courseContentId), body);
  }

  /**
   * Tutor List Courses
   */
  async tutorListCoursesTutorsCoursesGet({ courseFamilyId, description, fullPath, fullPathStudent, id, limit, organizationId, path, providerUrl, skip, title }: { courseFamilyId?: string | null; description?: string | null; fullPath?: string | null; fullPathStudent?: string | null; id?: string | null; limit?: number | null; organizationId?: string | null; path?: string | null; providerUrl?: string | null; skip?: number | null; title?: string | null }): Promise<CourseTutorList[]> {
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
    return this.client.get<CourseTutorList[]>(this.buildPath('courses'), { params: queryParams });
  }

  /**
   * Tutor Get Courses
   */
  async tutorGetCoursesTutorsCoursesCourseIdGet({ courseId }: { courseId: string | string }): Promise<CourseTutorGet> {
    return this.client.get<CourseTutorGet>(this.buildPath('courses', courseId));
  }
}
