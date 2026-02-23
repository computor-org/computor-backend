/**
 * Auto-generated client for WorkspacesClient.
 * Endpoint: /workspaces
 */

import type { WorkspaceRoleAssign, WorkspaceRoleUser } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class WorkspacesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/workspaces');
  }

  /**
   * Assign a workspace role by email
   * Assign _workspace_user or _workspace_maintainer to a user by email.
   */
  async assignRoleWorkspacesRolesAssignPost({ userId, body }: { userId?: string | null; body: WorkspaceRoleAssign }): Promise<WorkspaceRoleUser> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<WorkspaceRoleUser>(this.buildPath('roles', 'assign'), body, { params: queryParams });
  }

  /**
   * List all users with their workspace roles
   * List all users. Each user includes their workspace roles (empty list if none).
   */
  async listUsersWorkspacesRolesUsersGet({ userId }: { userId?: string | null }): Promise<WorkspaceRoleUser[]> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<WorkspaceRoleUser[]>(this.buildPath('roles', 'users'), { params: queryParams });
  }

  /**
   * Remove a workspace role from a user
   * Remove _workspace_user or _workspace_maintainer from a user.
   */
  async removeRoleWorkspacesRolesUsersUserIdRoleIdDelete({ roleId, userId }: { roleId: string; userId: string }): Promise<void> {
    return this.client.delete<void>(this.buildPath('roles', 'users', userId, roleId));
  }
}
