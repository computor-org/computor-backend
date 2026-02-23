/**
 * Client for workspace role management API.
 * Endpoint: /workspaces/roles
 */

import type {
  WorkspaceRoleUser,
  WorkspaceRoleAssign,
} from '@/src/types/workspaces';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from '@/src/generated/clients/baseClient';

export class WorkspaceRolesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/workspaces/roles');
  }

  /**
   * List all users with workspace roles.
   */
  async listUsers(): Promise<WorkspaceRoleUser[]> {
    return this.client.get<WorkspaceRoleUser[]>(this.buildPath('users'));
  }

  /**
   * Assign a workspace role to a user by email.
   */
  async assignRole({ body }: { body: WorkspaceRoleAssign }): Promise<WorkspaceRoleUser> {
    return this.client.post<WorkspaceRoleUser>(this.buildPath('assign'), body);
  }

  /**
   * Remove a workspace role from a user.
   */
  async removeRole({ userId, roleId }: { userId: string; roleId: string }): Promise<void> {
    return this.client.delete<void>(this.buildPath('users', userId, roleId));
  }
}
