/**
 * Auto-generated client for CourseContentsClient.
 * Endpoint: /course-contents
 */

import type { AssignExampleRequest, AvailableTeam, CourseContentCreate, CourseContentGet, CourseContentList, CourseContentUpdate, DeploymentSummary, DeploymentWithHistory, LeaveTeamResponse, TeamCreate, TeamResponse } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseContentsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-contents');
  }

  /**
   * List Course-Contents
   */
  async listCourseContentsCourseContentsGet({ archived, courseContentTypeId, courseId, description, exampleVersionId, hasDeployment, id, limit, maxGroupSize, maxSubmissions, maxTestRuns, path, position, skip, testingServiceId, title, userId }: { archived?: boolean | null; courseContentTypeId?: string | null; courseId?: string | null; description?: string | null; exampleVersionId?: string | null; hasDeployment?: boolean | null; id?: string | null; limit?: number | null; maxGroupSize?: number | null; maxSubmissions?: number | null; maxTestRuns?: number | null; path?: string | null; position?: number | null; skip?: number | null; testingServiceId?: string | null; title?: string | null; userId?: string | null }): Promise<CourseContentList[]> {
    const queryParams: Record<string, unknown> = {
      archived,
      course_content_type_id: courseContentTypeId,
      course_id: courseId,
      description,
      example_version_id: exampleVersionId,
      has_deployment: hasDeployment,
      id,
      limit,
      max_group_size: maxGroupSize,
      max_submissions: maxSubmissions,
      max_test_runs: maxTestRuns,
      path,
      position,
      skip,
      testing_service_id: testingServiceId,
      title,
      user_id: userId,
    };
    return this.client.get<CourseContentList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Course-Contents
   */
  async createCourseContentsCourseContentsPost({ userId, body }: { userId?: string | null; body: CourseContentCreate }): Promise<CourseContentGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseContentGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Get Course Deployment Summary
   * Get deployment summary for a course.
   * Shows statistics about example deployments in the course.
   */
  async getCourseDeploymentSummaryCourseContentsCoursesCourseIdDeploymentSummaryGet({ courseId, userId }: { courseId: string; userId?: string | null }): Promise<DeploymentSummary> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<DeploymentSummary>(this.buildPath('courses', courseId, 'deployment-summary'), { params: queryParams });
  }

  /**
   * Get Deployment Status With Workflow
   * Get detailed deployment status including Temporal workflow information.
   * Returns deployment data and checks the Temporal workflow status if one is running.
   */
  async getDeploymentStatusWithWorkflowCourseContentsDeploymentContentIdGet({ contentId, userId }: { contentId: string; userId?: string | null }): Promise<Record<string, unknown> & Record<string, unknown>> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<Record<string, unknown> & Record<string, unknown>>(this.buildPath('deployment', contentId), { params: queryParams });
  }

  /**
   * Assign Example To Content
   * Assign an example version to course content.
   * This creates or updates a deployment record, linking the example to the content.
   * Only submittable content (assignments) can have examples assigned.
   */
  async assignExampleToContentCourseContentsContentIdAssignExamplePost({ contentId, userId, body }: { contentId: string; userId?: string | null; body: AssignExampleRequest }): Promise<DeploymentWithHistory> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<DeploymentWithHistory>(this.buildPath(contentId, 'assign-example'), body, { params: queryParams });
  }

  /**
   * Get Content Deployment
   * Get deployment information for specific course content.
   * Returns deployment record with full history if exists.
   */
  async getContentDeploymentCourseContentsContentIdDeploymentGet({ contentId, userId }: { contentId: string; userId?: string | null }): Promise<DeploymentWithHistory | null> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<DeploymentWithHistory | null>(this.buildPath(contentId, 'deployment'), { params: queryParams });
  }

  /**
   * Unassign Example From Content
   * Remove example assignment from course content.
   * This updates the deployment record to unassigned status.
   * The actual removal from student-template happens during next generation.
   */
  async unassignExampleFromContentCourseContentsContentIdExampleDelete({ contentId, userId }: { contentId: string; userId?: string | null }): Promise<Record<string, unknown> & Record<string, string>> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<Record<string, unknown> & Record<string, string>>(this.buildPath(contentId, 'example'), { params: queryParams });
  }

  /**
   * Get Available Teams
   * Browse available teams that the current user can join.
   * Only shows teams that:
   * - Are in 'forming' status
   * - Have space for more members
   * - Are for the specified course content
   */
  async getAvailableTeamsCourseContentsCourseContentIdSubmissionGroupsAvailableGet({ courseContentId, userId }: { courseContentId: string; userId?: string | null }): Promise<AvailableTeam[]> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<AvailableTeam[]>(this.buildPath(courseContentId, 'submission-groups', 'available'), { params: queryParams });
  }

  /**
   * Leave My Team
   * Leave the current user's team for a course content.
   * If the user is the last member, the team is deleted.
   */
  async leaveMyTeamCourseContentsCourseContentIdSubmissionGroupsMyTeamDelete({ courseContentId, userId }: { courseContentId: string; userId?: string | null }): Promise<LeaveTeamResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<LeaveTeamResponse>(this.buildPath(courseContentId, 'submission-groups', 'my-team'), { params: queryParams });
  }

  /**
   * Get My Team
   * Get the current user's team for a course content.
   * Returns 404 if user doesn't have a team yet.
   */
  async getMyTeamCourseContentsCourseContentIdSubmissionGroupsMyTeamGet({ courseContentId, userId }: { courseContentId: string; userId?: string | null }): Promise<TeamResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<TeamResponse>(this.buildPath(courseContentId, 'submission-groups', 'my-team'), { params: queryParams });
  }

  /**
   * Create My Team
   * Create a new team for the current user for a course content.
   * Student endpoint - creates a team and adds the current user as the first member.
   */
  async createMyTeamCourseContentsCourseContentIdSubmissionGroupsMyTeamPost({ courseContentId, userId, body }: { courseContentId: string; userId?: string | null; body: TeamCreate }): Promise<TeamResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<TeamResponse>(this.buildPath(courseContentId, 'submission-groups', 'my-team'), body, { params: queryParams });
  }

  /**
   * Delete Course-Contents
   */
  async deleteCourseContentsCourseContentsIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Course-Contents
   */
  async getCourseContentsCourseContentsIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<CourseContentGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseContentGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Course-Contents
   */
  async updateCourseContentsCourseContentsIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: CourseContentUpdate }): Promise<CourseContentGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<CourseContentGet>(this.buildPath(id), body, { params: queryParams });
  }

  /**
   * Route Course-Contents
   */
  async routeCourseContentsCourseContentsIdArchivePatch({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<void>(this.buildPath(id, 'archive'), { params: queryParams });
  }
}
