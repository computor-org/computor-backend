/**
 * Auto-generated client for SystemClient.
 * Endpoint: /system
 */

import type { CourseFamilyTaskRequest, CourseTaskRequest, GenerateAssignmentsRequest, GenerateAssignmentsResponse, GenerateTemplateRequest, GenerateTemplateResponse, OrganizationTaskRequest, TaskResponse } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class SystemClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/system');
  }

  /**
   * Create Organization Async
   * Create an organization asynchronously using Temporal workflows.
   */
  async createOrganizationAsyncSystemDeployOrganizationsPost({ body }: { body: OrganizationTaskRequest }): Promise<TaskResponse> {
    return this.client.post<TaskResponse>(this.buildPath('deploy', 'organizations'), body);
  }

  /**
   * Create Course Family Async
   * Create a course family asynchronously using Temporal workflows.
   */
  async createCourseFamilyAsyncSystemDeployCourseFamiliesPost({ body }: { body: CourseFamilyTaskRequest }): Promise<TaskResponse> {
    return this.client.post<TaskResponse>(this.buildPath('deploy', 'course-families'), body);
  }

  /**
   * Create Course Async
   * Create a course asynchronously using Temporal workflows.
   */
  async createCourseAsyncSystemDeployCoursesPost({ body }: { body: CourseTaskRequest }): Promise<TaskResponse> {
    return this.client.post<TaskResponse>(this.buildPath('deploy', 'courses'), body);
  }

  /**
   * Generate Student Template
   * Generate student template from assigned examples (Git operations).
   * This is step 2 of the two-step process. It triggers a Temporal workflow
   * that will:
   * 1. Download examples from MinIO based on CourseContent assignments
   * 2. Process them according to meta.yaml rules
   * 3. Generate the student-template repository
   * 4. Commit and push the changes
   */
  async generateStudentTemplateSystemCoursesCourseIdGenerateStudentTemplatePost({ courseId, body }: { courseId: string; body: GenerateTemplateRequest }): Promise<GenerateTemplateResponse> {
    return this.client.post<GenerateTemplateResponse>(this.buildPath('courses', courseId, 'generate-student-template'), body);
  }

  /**
   * Generate Assignments
   */
  async generateAssignmentsSystemCoursesCourseIdGenerateAssignmentsPost({ courseId, body }: { courseId: string; body: GenerateAssignmentsRequest }): Promise<GenerateAssignmentsResponse> {
    return this.client.post<GenerateAssignmentsResponse>(this.buildPath('courses', courseId, 'generate-assignments'), body);
  }

  /**
   * Get Course Gitlab Status
   * Check GitLab configuration status for a course.
   * Returns information about GitLab integration and what's missing.
   */
  async getCourseGitlabStatusSystemCoursesCourseIdGitlabStatusGet({ courseId }: { courseId: string }): Promise<Record<string, unknown> & Record<string, unknown>> {
    return this.client.get<Record<string, unknown> & Record<string, unknown>>(this.buildPath('courses', courseId, 'gitlab-status'));
  }

  /**
   * Create Hierarchy
   * Create a complete organization -> course family -> course hierarchy from a configuration.
   * This endpoint accepts a deployment configuration and creates the entire hierarchy
   * using the DeployComputorHierarchyWorkflow Temporal workflow.
   */
  async createHierarchySystemHierarchyCreatePost({ body }: { body: Record<string, unknown> & Record<string, unknown> }): Promise<Record<string, unknown> & Record<string, unknown>> {
    return this.client.post<Record<string, unknown> & Record<string, unknown>>(this.buildPath('hierarchy', 'create'), body);
  }

  /**
   * Get Hierarchy Status
   * Get the status of a deployment workflow.
   * Returns the current status of the deployment workflow, including any errors
   * or the final result if completed.
   */
  async getHierarchyStatusSystemHierarchyStatusWorkflowIdGet({ workflowId }: { workflowId: string }): Promise<Record<string, unknown> & Record<string, unknown>> {
    return this.client.get<Record<string, unknown> & Record<string, unknown>>(this.buildPath('hierarchy', 'status', workflowId));
  }
}
