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
   * Tutor List Course Contents
   */
  async tutorListCourseContentsTutorsCourseMembersCourseMemberIdCourseContentsGet({ courseMemberId, skip, limit, id, title, path, courseId, courseContentTypeId, directory, project, providerUrl, nlevel, descendants, ascendants }: { courseMemberId: string | string; skip?: number | null; limit?: number | null; id?: string | null; title?: string | null; path?: string | null; courseId?: string | null; courseContentTypeId?: string | null; directory?: string | null; project?: string | null; providerUrl?: string | null; nlevel?: number | null; descendants?: string | null; ascendants?: string | null }): Promise<CourseContentStudentList[]> {
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
    return this.client.get<CourseContentStudentList[]>(this.buildPath('course-members', courseMemberId, 'course-contents'), { params: queryParams });
  }

  /**
   * Tutor Get Courses
   */
  async tutorGetCoursesTutorsCoursesCourseIdGet({ courseId }: { courseId: string | string }): Promise<CourseTutorGet> {
    return this.client.get<CourseTutorGet>(this.buildPath('courses', courseId));
  }

  /**
   * Tutor List Courses
   */
  async tutorListCoursesTutorsCoursesGet({ skip, limit, id, title, description, path, courseFamilyId, organizationId, providerUrl, fullPath, fullPathStudent }: { skip?: number | null; limit?: number | null; id?: string | null; title?: string | null; description?: string | null; path?: string | null; courseFamilyId?: string | null; organizationId?: string | null; providerUrl?: string | null; fullPath?: string | null; fullPathStudent?: string | null }): Promise<CourseTutorList[]> {
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
    return this.client.get<CourseTutorList[]>(this.buildPath('courses'), { params: queryParams });
  }

  /**
   * Tutor Get Course Members
   */
  async tutorGetCourseMembersTutorsCourseMembersCourseMemberIdGet({ courseMemberId }: { courseMemberId: string | string }): Promise<TutorCourseMemberGet> {
    return this.client.get<TutorCourseMemberGet>(this.buildPath('course-members', courseMemberId));
  }

  /**
   * Tutor List Course Members
   */
  async tutorListCourseMembersTutorsCourseMembersGet({ skip, limit, id, userId, courseId, courseGroupId, courseRoleId, givenName, familyName }: { skip?: number | null; limit?: number | null; id?: string | null; userId?: string | null; courseId?: string | null; courseGroupId?: string | null; courseRoleId?: string | null; givenName?: string | null; familyName?: string | null }): Promise<TutorCourseMemberList[]> {
    const queryParams: Record<string, unknown> = {
      skip,
      limit,
      id,
      user_id: userId,
      course_id: courseId,
      course_group_id: courseGroupId,
      course_role_id: courseRoleId,
      given_name: givenName,
      family_name: familyName,
    };
    return this.client.get<TutorCourseMemberList[]>(this.buildPath('course-members'), { params: queryParams });
  }
}
