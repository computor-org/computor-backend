/**
 * Client for Coder workspace management API.
 * Endpoint: /coder
 */

import type {
  CoderHealthResponse,
  TemplateListResponse,
  WorkspaceListResponse,
  WorkspaceDetails,
  WorkspaceActionResponse,
  WorkspaceProvisionRequest,
  ProvisionResult,
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
}
