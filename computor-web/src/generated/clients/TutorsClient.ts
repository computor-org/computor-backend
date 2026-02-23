/**
 * Auto-generated client for TutorsClient.
 * Endpoint: /tutors
 */

import type { CourseContentStudentGet, CourseContentStudentList, CourseTutorGet, CourseTutorList, TutorCourseMemberGet, TutorCourseMemberList, TutorGradeCreate, TutorGradeResponse, TutorSubmissionGroupGet, TutorSubmissionGroupList, TutorTestArtifactList, TutorTestCreateResponse, TutorTestGet, TutorTestStatus } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class TutorsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/tutors');
  }

  /**
   * Download Course Content Description
   * Download the content/description files for a course content as a ZIP file.
   * This endpoint allows tutors to download the assignment description files
   * which are stored in the 'content/' directory of the example.
   * This typically includes:
   * - index_<language_id>.md files (assignment descriptions in different languages)
   * - mediaFiles/ directory (images, attachments, etc.)
   * - Other supporting content files
   * Returns:
   * StreamingResponse containing a ZIP file with the content/ directory
   */
  async downloadCourseContentDescriptionTutorsCourseContentsCourseContentIdDescriptionGet({ courseContentId, userId }: { courseContentId: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<void>(this.buildPath('course-contents', courseContentId, 'description'), { params: queryParams });
  }

  /**
   * Download Course Content Reference
   * Download the reference/example solution for a course content as a ZIP file.
   * This endpoint allows tutors to download the reference solution files
   * associated with an assignment for grading purposes.
   * The files included are determined by the meta.yaml properties:
   * - properties.studentSubmissionFiles: Files that students must submit
   * - properties.additionalFiles: Additional files provided to students
   * These can be individual files or directories.
   * Returns:
   * StreamingResponse containing a ZIP file with the reference solution files
   */
  async downloadCourseContentReferenceTutorsCourseContentsCourseContentIdReferenceGet({ courseContentId, userId }: { courseContentId: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<void>(this.buildPath('course-contents', courseContentId, 'reference'), { params: queryParams });
  }

  /**
   * Create Tutor Test
   * Create and execute a tutor test for an assignment.
   * This endpoint allows tutors to test their own code against the reference
   * solution (test.yaml) for an assignment. Unlike student tests, tutor tests:
   * - Don't create database records (state in Redis only)
   * - Are ephemeral (automatically cleaned up after 1 hour)
   * - Don't affect grading or submission history
   * The tutor uploads a ZIP file containing their code (matching the structure
   * expected by studentSubmissionFiles in meta.yaml), and the system runs the
   * same tests that students would run.
   * **Permissions**: Requires tutor role or higher for the course.
   * **Request**:
   * - `file`: ZIP file with tutor's code (multipart/form-data)
   * - `config`: Optional JSON string with configuration:
   * - `store_graphics_artifacts`: bool (default: true)
   * - `timeout_seconds`: int (optional, uses service default)
   * **Response**: Returns test_id for polling status via GET /tutors/tests/{test_id}
   */
  async createTutorTestTutorsCourseContentsCourseContentIdTestPost({ courseContentId, userId }: { courseContentId: string | string; userId?: string | null }): Promise<TutorTestCreateResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<TutorTestCreateResponse>(this.buildPath('course-contents', courseContentId, 'test'), { params: queryParams });
  }

  /**
   * Tutor List Course Members Endpoint
   * List course members for tutors.
   */
  async tutorListCourseMembersEndpointTutorsCourseMembersGet({ courseGroupId, courseId, courseRoleId, familyName, givenName, id, limit, skip, userId }: { courseGroupId?: string | null; courseId?: string | null; courseRoleId?: string | null; familyName?: string | null; givenName?: string | null; id?: string | null; limit?: number | null; skip?: number | null; userId?: string | null }): Promise<TutorCourseMemberList[]> {
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
   * Tutor Get Course Members Endpoint
   * Get a course member with unreviewed course contents.
   */
  async tutorGetCourseMembersEndpointTutorsCourseMembersCourseMemberIdGet({ courseMemberId, userId }: { courseMemberId: string | string; userId?: string | null }): Promise<TutorCourseMemberGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<TutorCourseMemberGet>(this.buildPath('course-members', courseMemberId), { params: queryParams });
  }

  /**
   * Tutor List Course Contents Endpoint
   * List course contents for a course member as a tutor.
   */
  async tutorListCourseContentsEndpointTutorsCourseMembersCourseMemberIdCourseContentsGet({ courseMemberId, ascendants, courseContentTypeId, courseId, descendants, directory, id, limit, nlevel, path, project, providerUrl, skip, title }: { courseMemberId: string | string; ascendants?: string | null; courseContentTypeId?: string | null; courseId?: string | null; descendants?: string | null; directory?: string | null; id?: string | null; limit?: number | null; nlevel?: number | null; path?: string | null; project?: string | null; providerUrl?: string | null; skip?: number | null; title?: string | null }): Promise<CourseContentStudentList[]> {
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
   * Tutor Get Course Contents Endpoint
   * Get course content for a course member as a tutor.
   */
  async tutorGetCourseContentsEndpointTutorsCourseMembersCourseMemberIdCourseContentsCourseContentIdGet({ courseContentId, courseMemberId }: { courseContentId: string | string; courseMemberId: string | string }): Promise<CourseContentStudentGet> {
    return this.client.get<CourseContentStudentGet>(this.buildPath('course-members', courseMemberId, 'course-contents', courseContentId));
  }

  /**
   * Tutor Update Course Contents Endpoint
   * Update grade for a course content as a tutor.
   */
  async tutorUpdateCourseContentsEndpointTutorsCourseMembersCourseMemberIdCourseContentsCourseContentIdPatch({ courseContentId, courseMemberId, userId, body }: { courseContentId: string | string; courseMemberId: string | string; userId?: string | null; body: TutorGradeCreate }): Promise<TutorGradeResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<TutorGradeResponse>(this.buildPath('course-members', courseMemberId, 'course-contents', courseContentId), body, { params: queryParams });
  }

  /**
   * Tutor List Courses Endpoint
   * List courses for tutors.
   */
  async tutorListCoursesEndpointTutorsCoursesGet({ courseFamilyId, description, fullPath, fullPathStudent, id, limit, organizationId, path, providerUrl, skip, title }: { courseFamilyId?: string | null; description?: string | null; fullPath?: string | null; fullPathStudent?: string | null; id?: string | null; limit?: number | null; organizationId?: string | null; path?: string | null; providerUrl?: string | null; skip?: number | null; title?: string | null }): Promise<CourseTutorList[]> {
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
   * Tutor Get Courses Endpoint
   * Get a course for tutors.
   */
  async tutorGetCoursesEndpointTutorsCoursesCourseIdGet({ courseId }: { courseId: string | string }): Promise<CourseTutorGet> {
    return this.client.get<CourseTutorGet>(this.buildPath('courses', courseId));
  }

  /**
   * Tutor List Submission Groups Endpoint
   * List submission groups for tutors with filtering options.
   * Query parameters:
   * - course_id: Filter by course ID
   * - course_content_id: Filter by course content ID
   * - course_group_id: Filter by course group ID
   * - has_submissions: Filter groups with/without submissions
   * - has_ungraded_submissions: Filter groups with/without ungraded submissions
   * - limit: Maximum number of results (default: 100)
   * - offset: Number of results to skip (default: 0)
   */
  async tutorListSubmissionGroupsEndpointTutorsSubmissionGroupsGet({ courseContentId, courseGroupId, courseId, hasSubmissions, hasUngradedSubmissions, limit, offset, userId }: { courseContentId?: string | null; courseGroupId?: string | null; courseId?: string | null; hasSubmissions?: boolean | null; hasUngradedSubmissions?: boolean | null; limit?: number; offset?: number; userId?: string | null }): Promise<TutorSubmissionGroupList[]> {
    const queryParams: Record<string, unknown> = {
      course_content_id: courseContentId,
      course_group_id: courseGroupId,
      course_id: courseId,
      has_submissions: hasSubmissions,
      has_ungraded_submissions: hasUngradedSubmissions,
      limit,
      offset,
      user_id: userId,
    };
    return this.client.get<TutorSubmissionGroupList[]>(this.buildPath('submission-groups'), { params: queryParams });
  }

  /**
   * Tutor Get Submission Group Endpoint
   * Get a submission group with detailed information for tutors.
   */
  async tutorGetSubmissionGroupEndpointTutorsSubmissionGroupsSubmissionGroupIdGet({ submissionGroupId, userId }: { submissionGroupId: string | string; userId?: string | null }): Promise<TutorSubmissionGroupGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<TutorSubmissionGroupGet>(this.buildPath('submission-groups', submissionGroupId), { params: queryParams });
  }

  /**
   * Get Tutor Test Endpoint
   * Get full tutor test details including result_dict.
   * Returns the complete test information including the full result_dict
   * from MinIO (result.json). Use GET /tutors/tests/{test_id}/status for
   * quick polling without the full result data.
   * **Permissions**: Only the test owner or admin can access test details.
   * Tests are ephemeral and expire after 1 hour.
   */
  async getTutorTestEndpointTutorsTestsTestIdGet({ testId }: { testId: string }): Promise<TutorTestGet> {
    return this.client.get<TutorTestGet>(this.buildPath('tests', testId));
  }

  /**
   * List Tutor Test Artifacts Endpoint
   * List all artifacts from a tutor test.
   * Returns metadata about each artifact file.
   * **Permissions**: Only the test owner or admin can list artifacts.
   */
  async listTutorTestArtifactsEndpointTutorsTestsTestIdArtifactsGet({ testId }: { testId: string }): Promise<TutorTestArtifactList> {
    return this.client.get<TutorTestArtifactList>(this.buildPath('tests', testId, 'artifacts'));
  }

  /**
   * Download Tutor Test Artifacts
   * Download all artifacts from a tutor test as a ZIP file.
   * Artifacts include generated files such as plots, figures, and debug output
   * created during test execution.
   * **Permissions**: Only the test owner or admin can download artifacts.
   */
  async downloadTutorTestArtifactsTutorsTestsTestIdArtifactsDownloadGet({ testId }: { testId: string }): Promise<void> {
    return this.client.get<void>(this.buildPath('tests', testId, 'artifacts', 'download'));
  }

  /**
   * Get Tutor Test Status Endpoint
   * Get quick status of a tutor test (for polling).
   * Use this endpoint to poll for completion status.
   * For full test results, use GET /tutors/tests/{test_id}.
   * **Status values**:
   * - `pending`: Test is queued
   * - `running`: Test is executing
   * - `completed`: Test finished successfully
   * - `failed`: Test failed
   * **Permissions**: Only the test owner or admin can check status.
   * Tests are ephemeral and expire after 1 hour.
   */
  async getTutorTestStatusEndpointTutorsTestsTestIdStatusGet({ testId }: { testId: string }): Promise<TutorTestStatus> {
    return this.client.get<TutorTestStatus>(this.buildPath('tests', testId, 'status'));
  }
}
