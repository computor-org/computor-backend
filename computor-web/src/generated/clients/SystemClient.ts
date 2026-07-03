/**
 * Auto-generated client for SystemClient.
 * Endpoint: /system
 */

import type { CourseTaskRequest, GenerateAssignmentsRequest, GenerateAssignmentsResponse, GenerateTemplateRequest, GenerateTemplateResponse, MaintenanceActivate, MaintenanceSchedule, MaintenanceStatusGet, TaskResponse } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class SystemClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/system');
  }

  /**
   * Generate Assignments
   */
  async generateAssignmentsSystemCoursesCourseIdGenerateAssignmentsPost({ courseId, userId, body }: { courseId: string; userId?: string | null; body: GenerateAssignmentsRequest }): Promise<GenerateAssignmentsResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<GenerateAssignmentsResponse>(this.buildPath('courses', courseId, 'generate-assignments'), body, { params: queryParams });
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
  async generateStudentTemplateSystemCoursesCourseIdGenerateStudentTemplatePost({ courseId, userId, body }: { courseId: string; userId?: string | null; body: GenerateTemplateRequest }): Promise<GenerateTemplateResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<GenerateTemplateResponse>(this.buildPath('courses', courseId, 'generate-student-template'), body, { params: queryParams });
  }

  /**
   * Get Course Gitlab Status
   * Check GitLab configuration status for a course.
   * Returns information about GitLab integration and what's missing.
   */
  async getCourseGitlabStatusSystemCoursesCourseIdGitlabStatusGet({ courseId, userId }: { courseId: string; userId?: string | null }): Promise<Record<string, unknown> & Record<string, unknown>> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<Record<string, unknown> & Record<string, unknown>>(this.buildPath('courses', courseId, 'gitlab-status'), { params: queryParams });
  }

  /**
   * Create Course Async
   * Create a course asynchronously using Temporal workflows.
   */
  async createCourseAsyncSystemDeployCoursesPost({ userId, body }: { userId?: string | null; body: CourseTaskRequest }): Promise<TaskResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<TaskResponse>(this.buildPath('deploy', 'courses'), body, { params: queryParams });
  }

  /**
   * Create Hierarchy
   * Create a complete organization -> course family -> course hierarchy from a configuration.
   * This endpoint accepts a deployment configuration and creates the entire hierarchy
   * using the DeployComputorHierarchyWorkflow Temporal workflow.
   */
  async createHierarchySystemHierarchyCreatePost({ userId, body }: { userId?: string | null; body: Record<string, unknown> & Record<string, unknown> }): Promise<Record<string, unknown> & Record<string, unknown>> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<Record<string, unknown> & Record<string, unknown>>(this.buildPath('hierarchy', 'create'), body, { params: queryParams });
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

  /**
   * Activate Maintenance
   * Activate maintenance mode immediately.
   * Admin only. Blocks all mutating requests (POST/PUT/PATCH/DELETE) for non-admin users.
   * GET requests, auth endpoints, and admin requests remain accessible.
   */
  async activateMaintenanceSystemMaintenanceActivatePost({ userId, body }: { userId?: string | null; body: MaintenanceActivate }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<void>(this.buildPath('maintenance', 'activate'), body, { params: queryParams });
  }

  /**
   * Deactivate Maintenance
   * Deactivate maintenance mode.
   * Admin only. Immediately restores full service for all users.
   */
  async deactivateMaintenanceSystemMaintenanceDeactivatePost(): Promise<void> {
    return this.client.post<void>(this.buildPath('maintenance', 'deactivate'));
  }

  /**
   * Cancel Scheduled Maintenance
   * Cancel scheduled maintenance.
   */
  async cancelScheduledMaintenanceSystemMaintenanceScheduleDelete(): Promise<void> {
    return this.client.delete<void>(this.buildPath('maintenance', 'schedule'));
  }

  /**
   * Schedule Maintenance
   * Schedule future maintenance.
   * Admin only. Sets a scheduled time and optionally notifies connected users.
   * Does NOT activate maintenance mode -- that requires a separate activate call
   * or can be triggered by the maintenance.sh script.
   */
  async scheduleMaintenanceSystemMaintenanceSchedulePost({ userId, body }: { userId?: string | null; body: MaintenanceSchedule }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<void>(this.buildPath('maintenance', 'schedule'), body, { params: queryParams });
  }

  /**
   * Get Maintenance Status
   * Get current maintenance status.
   * Available to all authenticated users.
   * Returns both active maintenance state and any scheduled maintenance.
   */
  async getMaintenanceStatusSystemMaintenanceStatusGet(): Promise<MaintenanceStatusGet> {
    return this.client.get<MaintenanceStatusGet>(this.buildPath('maintenance', 'status'));
  }
}
