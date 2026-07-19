/**
 * Client for Coder workspace management API.
 * Endpoint: /coder
 */

import type {
  CoderHealthResponse,
  CourseWorkspaceAdminListResponse,
  TemplateListResponse,
  WorkspaceListResponse,
  WorkspaceDetails,
  WorkspaceActionResponse,
  WorkspaceProvisionRequest,
  ProvisionResult,
  ImageBuildRequest,
  TemplatePushRequest,
  WorkspaceRolloutRequest,
  CoderAdminTaskResponse,
  TaskInfo,
  CoderAdminTaskListResponse,
  CoderFleetStatusResponse,
  TemplateSettingsListResponse,
  TemplateFileActionResponse,
  TemplateFilesResponse,
  TemplateVariablesResponse,
  WorkspaceTemplateSettings,
  WorkspaceTemplateSettingsUpdate,
} from '@/src/types/workspaces';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from '@/src/generated/clients/baseClient';

export class CoderClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/coder');
  }

  /**
   * Check Coder server health.
   */
  async getHealth(): Promise<CoderHealthResponse> {
    return this.client.get<CoderHealthResponse>(this.buildPath('health'));
  }

  /**
   * List available workspace templates.
   */
  async listTemplates(): Promise<TemplateListResponse> {
    return this.client.get<TemplateListResponse>(this.buildPath('templates'));
  }

  /**
   * List workspaces. If email is provided, lists workspaces for that user (admin only).
   */
  async listWorkspaces({ email }: { email?: string } = {}): Promise<WorkspaceListResponse> {
    const queryParams: Record<string, unknown> = { email };
    return this.client.get<WorkspaceListResponse>(this.buildPath('workspaces'), { params: queryParams });
  }

  /**
   * Check if a user has any workspaces.
   */
  async checkWorkspaceExists({ email }: { email: string }): Promise<boolean> {
    const queryParams: Record<string, unknown> = { email };
    return this.client.get<boolean>(this.buildPath('workspaces', 'exists'), { params: queryParams });
  }

  /**
   * Get detailed information about a specific workspace.
   */
  async getWorkspaceDetails({ username, workspaceName }: { username: string; workspaceName: string }): Promise<WorkspaceDetails> {
    return this.client.get<WorkspaceDetails>(this.buildPath('workspaces', username, workspaceName));
  }

  /**
   * Provision a new workspace.
   */
  async provisionWorkspace({ body }: { body: WorkspaceProvisionRequest }): Promise<ProvisionResult> {
    return this.client.post<ProvisionResult>(this.buildPath('workspaces', 'provision'), body);
  }

  /**
   * Start a workspace.
   */
  async startWorkspace({ username, workspaceName }: { username: string; workspaceName: string }): Promise<WorkspaceActionResponse> {
    return this.client.post<WorkspaceActionResponse>(this.buildPath('workspaces', username, workspaceName, 'start'));
  }

  /**
   * Stop a workspace.
   */
  async stopWorkspace({ username, workspaceName }: { username: string; workspaceName: string }): Promise<WorkspaceActionResponse> {
    return this.client.post<WorkspaceActionResponse>(this.buildPath('workspaces', username, workspaceName, 'stop'));
  }

  /**
   * Delete a workspace.
   */
  async deleteWorkspace({ username, workspaceName }: { username: string; workspaceName: string }): Promise<WorkspaceActionResponse> {
    return this.client.delete<WorkspaceActionResponse>(this.buildPath('workspaces', username, workspaceName));
  }

  // --- Admin: fleet view + extension rollout (workspace:manage) ---

  /**
   * List every workspace on the server, across all users (admin fleet view).
   */
  async listAllWorkspaces(): Promise<WorkspaceListResponse> {
    return this.client.get<WorkspaceListResponse>(this.buildPath('workspaces', 'all'));
  }

  /** Template-centric readiness, workspace counts, and privileged Coder health. */
  async getFleetStatus(): Promise<CoderFleetStatusResponse> {
    return this.client.get<CoderFleetStatusResponse>(this.buildPath('admin', 'fleet'));
  }

  /**
   * Build workspace Docker images (optionally a specific image tag).
   */
  async buildImages(body: ImageBuildRequest = {}): Promise<CoderAdminTaskResponse> {
    return this.client.post<CoderAdminTaskResponse>(this.buildPath('admin', 'images', 'build'), body);
  }

  /**
   * Push Coder templates (optionally building images first).
   */
  async pushTemplates(body: TemplatePushRequest = {}): Promise<CoderAdminTaskResponse> {
    return this.client.post<CoderAdminTaskResponse>(this.buildPath('admin', 'templates', 'push'), body);
  }

  /**
   * Roll existing workspaces onto their template's active version.
   */
  async rolloutWorkspaces(body: WorkspaceRolloutRequest = {}): Promise<CoderAdminTaskResponse> {
    return this.client.post<CoderAdminTaskResponse>(this.buildPath('admin', 'templates', 'rollout'), body);
  }

  /**
   * Poll the status of an admin task (image build / template push / rollout).
   */
  async getAdminTask(workflowId: string): Promise<TaskInfo> {
    return this.client.get<TaskInfo>(this.buildPath('admin', 'tasks', workflowId));
  }


  /** Recent build/push/rollout workflows, including active progress after reload. */
  async listAdminTasks(limit = 10): Promise<CoderAdminTaskListResponse> {
    return this.client.get<CoderAdminTaskListResponse>(this.buildPath('admin', 'tasks'), {
      params: { limit },
    });
  }

  /** All courses with their workspace configuration (admin Courses tab). */
  async listAdminCourses(): Promise<CourseWorkspaceAdminListResponse> {
    return this.client.get<CourseWorkspaceAdminListResponse>(
      this.buildPath('admin', 'courses'),
    );
  }

  // --- Admin: per-template settings + template editing (workspace:manage) ---

  /** All stored per-template settings (resource limits, seat quota, overrides). */
  async listTemplateSettings(): Promise<TemplateSettingsListResponse> {
    return this.client.get<TemplateSettingsListResponse>(
      this.buildPath('admin', 'templates', 'settings'),
    );
  }

  /** Upsert one template's settings. Limits/overrides apply at the next push. */
  async updateTemplateSettings({ templateName, body }: {
    templateName: string;
    body: WorkspaceTemplateSettingsUpdate;
  }): Promise<WorkspaceTemplateSettings> {
    return this.client.put<WorkspaceTemplateSettings>(
      this.buildPath('admin', 'templates', templateName, 'settings'),
      body,
    );
  }

  /** Contents of the deployed template directory's editable files. */
  async getTemplateFiles({ templateName }: { templateName: string }): Promise<TemplateFilesResponse> {
    return this.client.get<TemplateFilesResponse>(
      this.buildPath('admin', 'templates', templateName, 'files'),
    );
  }

  /** Overwrite one template file (raw editing); marks the template customized. */
  async updateTemplateFile({ templateName, fileName, content }: {
    templateName: string;
    fileName: string;
    content: string;
  }): Promise<TemplateFileActionResponse> {
    return this.client.put<TemplateFileActionResponse>(
      this.buildPath('admin', 'templates', templateName, 'files', fileName),
      { content },
    );
  }

  /** Hand a customized template back to automatic repo syncing (next startup). */
  async restoreTemplateManaged({ templateName }: { templateName: string }): Promise<TemplateFileActionResponse> {
    return this.client.post<TemplateFileActionResponse>(
      this.buildPath('admin', 'templates', templateName, 'restore-managed'),
    );
  }

  /** Declared Terraform variables of a template (settings-override pick-list). */
  async getTemplateVariables({ templateName }: { templateName: string }): Promise<TemplateVariablesResponse> {
    return this.client.get<TemplateVariablesResponse>(
      this.buildPath('admin', 'templates', templateName, 'variables'),
    );
  }
}
