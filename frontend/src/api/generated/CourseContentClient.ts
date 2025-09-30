/**
 * Auto-generated client for CourseContentInterface.
 * Endpoint: /course-contents
 */

import type { AssignExampleRequest, CourseContentCreate, CourseContentGet, CourseContentList, CourseContentQuery, CourseContentUpdate, DeploymentSummary, DeploymentWithHistory } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseContentClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-contents');
  }

  async create(payload: CourseContentCreate): Promise<CourseContentGet> {
    return this.client.post<CourseContentGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<CourseContentGet> {
    return this.client.get<CourseContentGet>(this.buildPath(id));
  }

  async list(params?: CourseContentQuery): Promise<CourseContentList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<CourseContentList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: CourseContentUpdate): Promise<CourseContentGet> {
    return this.client.patch<CourseContentGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }

  async archive(id: string | number): Promise<void> {
    await this.client.patch<void>(this.buildPath(id, 'archive'));
  }

  /**
   * Get Course Content Meta
   * Get file content from course content directory.
   */
  async getCourseContentMetaCourseContentsFilesCourseContentIdGet({ courseContentId, filename }: { courseContentId: string | string; filename?: string | null }): Promise<Record<string, unknown> & Record<string, unknown>> {
    const queryParams: Record<string, unknown> = {
      filename,
    };
    return this.client.get<Record<string, unknown> & Record<string, unknown>>(this.buildPath('files', courseContentId), { params: queryParams });
  }

  /**
   * Assign Example To Content
   * Assign an example version to course content.
   * This creates or updates a deployment record, linking the example to the content.
   * Only submittable content (assignments) can have examples assigned.
   */
  async assignExampleToContentCourseContentsContentIdAssignExamplePost({ contentId, body }: { contentId: string; body: AssignExampleRequest }): Promise<DeploymentWithHistory> {
    return this.client.post<DeploymentWithHistory>(this.buildPath(contentId, 'assign-example'), body);
  }

  /**
   * Unassign Example From Content
   * Remove example assignment from course content.
   * This updates the deployment record to unassigned status.
   * The actual removal from student-template happens during next generation.
   */
  async unassignExampleFromContentCourseContentsContentIdExampleDelete({ contentId }: { contentId: string }): Promise<Record<string, unknown> & Record<string, string>> {
    return this.client.delete<Record<string, unknown> & Record<string, string>>(this.buildPath(contentId, 'example'));
  }

  /**
   * Get Deployment Status With Workflow
   * Get detailed deployment status including Temporal workflow information.
   * Returns deployment data and checks the Temporal workflow status if one is running.
   */
  async getDeploymentStatusWithWorkflowCourseContentsDeploymentContentIdGet({ contentId }: { contentId: string }): Promise<Record<string, unknown> & Record<string, unknown>> {
    return this.client.get<Record<string, unknown> & Record<string, unknown>>(this.buildPath('deployment', contentId));
  }

  /**
   * Get Course Deployment Summary
   * Get deployment summary for a course.
   * Shows statistics about example deployments in the course.
   */
  async getCourseDeploymentSummaryCourseContentsCoursesCourseIdDeploymentSummaryGet({ courseId }: { courseId: string }): Promise<DeploymentSummary> {
    return this.client.get<DeploymentSummary>(this.buildPath('courses', courseId, 'deployment-summary'));
  }

  /**
   * Get Content Deployment
   * Get deployment information for specific course content.
   * Returns deployment record with full history if exists.
   */
  async getContentDeploymentCourseContentsContentIdDeploymentGet({ contentId }: { contentId: string }): Promise<DeploymentWithHistory | null> {
    return this.client.get<DeploymentWithHistory | null>(this.buildPath(contentId, 'deployment'));
  }

  /**
   * Route Course-Contents
   */
  async routeCourseContentsCourseContentsIdArchivePatch({ id }: { id: string | string }): Promise<void> {
    return this.client.patch<void>(this.buildPath(id, 'archive'));
  }
}
