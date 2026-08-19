/**
 * Auto-generated client for CoursesClient.
 * Endpoint: /courses
 */

import type { CascadeDeleteResult, CourseCreate, CourseGet, CourseGitBindingGet, CourseGitBindingUpsert, CourseList, CourseStudentWorkspacesResponse, CourseUpdate, CourseWorkspaceSettingsGet, CourseWorkspaceSettingsUpdate, StudentWorkspaceProvisionRequest, StudentWorkspaceProvisionResponse, WorkspaceActionResponse } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CoursesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/courses');
  }

  /**
   * List Courses
   */
  async listCoursesCoursesGet({ courseFamilyId, description, fullPath, id, languageCode, limit, maxSubmissions, maxTestRuns, organizationId, path, providerUrl, skip, title, userId, visible }: { courseFamilyId?: string | null; description?: string | null; fullPath?: string | null; id?: string | null; languageCode?: string | null; limit?: number | null; maxSubmissions?: number | null; maxTestRuns?: number | null; organizationId?: string | null; path?: string | null; providerUrl?: string | null; skip?: number | null; title?: string | null; userId?: string | null; visible?: boolean | null }): Promise<CourseList[]> {
    const queryParams: Record<string, unknown> = {
      course_family_id: courseFamilyId,
      description,
      full_path: fullPath,
      id,
      language_code: languageCode,
      limit,
      max_submissions: maxSubmissions,
      max_test_runs: maxTestRuns,
      organization_id: organizationId,
      path,
      provider_url: providerUrl,
      skip,
      title,
      user_id: userId,
      visible,
    };
    return this.client.get<CourseList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Courses
   */
  async createCoursesCoursesPost({ userId, body }: { userId?: string | null; body: CourseCreate }): Promise<CourseGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete course and all course-specific data
   * Delete a course and ALL its data including:
   * - All course members (NOT the users themselves)
   * - All course groups
   * - All course content types and contents
   * - All submission groups and their artifacts
   * - All results and grades
   * - All messages targeted to the course
   * **WARNING**: This is a destructive operation. Use dry_run=true to preview.
   */
  async deleteCourseEndpointCoursesCourseIdDelete({ courseId, dryRun, userId }: { courseId: string; dryRun?: boolean; userId?: string | null }): Promise<CascadeDeleteResult> {
    const queryParams: Record<string, unknown> = {
      dry_run: dryRun,
      user_id: userId,
    };
    return this.client.delete<CascadeDeleteResult>(this.buildPath(courseId), { params: queryParams });
  }

  /**
   * Get Course Git Binding Endpoint
   * Full git binding for a course (lecturer cohort only).
   */
  async getCourseGitBindingEndpointCoursesCourseIdGitGet({ courseId, userId }: { courseId: string | string; userId?: string | null }): Promise<CourseGitBindingGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseGitBindingGet>(this.buildPath(courseId, 'git'), { params: queryParams });
  }

  /**
   * Upsert Course Git Binding Endpoint
   * Create or replace the course's git binding (lecturer cohort only).
   */
  async upsertCourseGitBindingEndpointCoursesCourseIdGitPut({ courseId, userId, body }: { courseId: string | string; userId?: string | null; body: CourseGitBindingUpsert }): Promise<CourseGitBindingGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.put<CourseGitBindingGet>(this.buildPath(courseId, 'git'), body, { params: queryParams });
  }

  /**
   * List Student Workspaces Endpoint
   * Course members' workspaces on course-allowed templates (lecturer view).
   */
  async listStudentWorkspacesEndpointCoursesCourseIdStudentWorkspacesGet({ courseId, userId }: { courseId: string | string; userId?: string | null }): Promise<CourseStudentWorkspacesResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseStudentWorkspacesResponse>(this.buildPath(courseId, 'student-workspaces'), { params: queryParams });
  }

  /**
   * Provision Student Workspaces Endpoint
   * Bulk-provision (throwaway) workspaces for selected course members.
   */
  async provisionStudentWorkspacesEndpointCoursesCourseIdStudentWorkspacesProvisionPost({ courseId, userId, body }: { courseId: string | string; userId?: string | null; body: StudentWorkspaceProvisionRequest }): Promise<StudentWorkspaceProvisionResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<StudentWorkspaceProvisionResponse>(this.buildPath(courseId, 'student-workspaces', 'provision'), body, { params: queryParams });
  }

  /**
   * Delete Student Workspace Endpoint
   * Delete a member's throwaway workspace (lecturers: scratch-home only).
   */
  async deleteStudentWorkspaceEndpointCoursesCourseIdStudentWorkspacesUsernameWorkspaceNameDelete({ courseId, username, workspaceName, userId }: { courseId: string | string; username: string; workspaceName: string; userId?: string | null }): Promise<WorkspaceActionResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<WorkspaceActionResponse>(this.buildPath(courseId, 'student-workspaces', username, workspaceName), { params: queryParams });
  }

  /**
   * Download the course template as a ZIP
   * Download the current course template, flat or re-arranged hierarchically.
   * Rate limit: 10 downloads per minute per user (429 once exhausted).
   */
  async downloadCourseTemplateCoursesCourseIdTemplateGet({ courseId, hierarchical, userId }: { courseId: string; hierarchical?: boolean; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      hierarchical,
      user_id: userId,
    };
    return this.client.get<void>(this.buildPath(courseId, 'template'), { params: queryParams });
  }

  /**
   * Get Course Workspace Settings Endpoint
   * Course workspace configuration (members read, managers get the picker).
   */
  async getCourseWorkspaceSettingsEndpointCoursesCourseIdWorkspaceSettingsGet({ courseId, userId }: { courseId: string | string; userId?: string | null }): Promise<CourseWorkspaceSettingsGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseWorkspaceSettingsGet>(this.buildPath(courseId, 'workspace-settings'), { params: queryParams });
  }

  /**
   * Update Course Workspace Settings Endpoint
   * Replace the course's allowed templates and flags (workspace:manage).
   */
  async updateCourseWorkspaceSettingsEndpointCoursesCourseIdWorkspaceSettingsPut({ courseId, userId, body }: { courseId: string | string; userId?: string | null; body: CourseWorkspaceSettingsUpdate }): Promise<CourseWorkspaceSettingsGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.put<CourseWorkspaceSettingsGet>(this.buildPath(courseId, 'workspace-settings'), body, { params: queryParams });
  }

  /**
   * Apply Course Workspace Policy Endpoint
   * Push the course's current root/internet policy onto its RUNNING
   * workspaces, restarting them (workspace:manage).
   * Stopped workspaces are left alone and reported: they pick the policy up on
   * their next start, which is cheaper and less surprising than starting a
   * student's workspace in order to lock it down.
   */
  async applyCourseWorkspacePolicyEndpointCoursesCourseIdWorkspaceSettingsApplyPolicyPost({ courseId, userId }: { courseId: string | string; userId?: string | null }): Promise<StudentWorkspaceProvisionResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<StudentWorkspaceProvisionResponse>(this.buildPath(courseId, 'workspace-settings', 'apply-policy'), { params: queryParams });
  }

  /**
   * Get Courses
   */
  async getCoursesCoursesIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<CourseGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Courses
   */
  async updateCoursesCoursesIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: CourseUpdate }): Promise<CourseGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<CourseGet>(this.buildPath(id), body, { params: queryParams });
  }
}
