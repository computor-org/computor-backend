/**
 * Client for course-scoped workspace configuration and the lecturer console.
 * Endpoints: /courses/{id}/workspace-settings, /courses/{id}/student-workspaces
 */

import type {
  CourseStudentWorkspacesResponse,
  CourseWorkspaceSettingsGet,
  CourseWorkspaceSettingsUpdate,
  StudentWorkspaceProvisionRequest,
  StudentWorkspaceProvisionResponse,
  WorkspaceActionResponse,
} from '@/src/types/workspaces';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from '@/src/generated/clients/baseClient';

export class CourseWorkspacesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/courses');
  }

  /** Course workspace configuration; members read, managers get the picker. */
  async getSettings({ courseId }: { courseId: string }): Promise<CourseWorkspaceSettingsGet> {
    return this.client.get<CourseWorkspaceSettingsGet>(
      this.buildPath(courseId, 'workspace-settings'),
    );
  }

  /** Replace the course's allowed templates and flags (workspace:manage). */
  async updateSettings({ courseId, body }: {
    courseId: string;
    body: CourseWorkspaceSettingsUpdate;
  }): Promise<CourseWorkspaceSettingsGet> {
    return this.client.put<CourseWorkspaceSettingsGet>(
      this.buildPath(courseId, 'workspace-settings'),
      body,
    );
  }

  /** Bulk-provision (throwaway) workspaces for selected course members. */
  async provisionStudents({ courseId, body }: {
    courseId: string;
    body: StudentWorkspaceProvisionRequest;
  }): Promise<StudentWorkspaceProvisionResponse> {
    return this.client.post<StudentWorkspaceProvisionResponse>(
      this.buildPath(courseId, 'student-workspaces', 'provision'),
      body,
    );
  }

  /** Course members' workspaces on course-allowed templates (lecturer view). */
  async listStudentWorkspaces({ courseId }: { courseId: string }): Promise<CourseStudentWorkspacesResponse> {
    return this.client.get<CourseStudentWorkspacesResponse>(
      this.buildPath(courseId, 'student-workspaces'),
    );
  }

  /** Delete a member's workspace (lecturers: scratch-home only). */
  async deleteStudentWorkspace({ courseId, username, workspaceName }: {
    courseId: string;
    username: string;
    workspaceName: string;
  }): Promise<WorkspaceActionResponse> {
    return this.client.delete<WorkspaceActionResponse>(
      this.buildPath(courseId, 'student-workspaces', username, workspaceName),
    );
  }
}
