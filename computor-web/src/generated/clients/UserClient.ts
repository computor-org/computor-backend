/**
 * Auto-generated client for UserClient.
 * Endpoint: /user-roles
 */

import type { UserRoleCreate, UserRoleGet, UserRoleList } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class UserClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/user-roles');
  }

  /**
   * List User Roles
   * List user roles.
   */
  async listUserRolesUserRolesGet({ limit, roleId, skip, userId }: { limit?: number | null; roleId?: string | null; skip?: number | null; userId?: string | null }): Promise<UserRoleList[]> {
    const queryParams: Record<string, unknown> = {
      limit,
      role_id: roleId,
      skip,
      user_id: userId,
    };
    return this.client.get<UserRoleList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create User Role
   * Create a new user role.
   */
  async createUserRoleUserRolesPost({ userId, body }: { userId?: string | null; body: UserRoleCreate }): Promise<UserRoleGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<UserRoleGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete User Role Endpoint
   * Delete a user role.
   */
  async deleteUserRoleEndpointUserRolesUsersUserIdRolesRoleIdDelete({ roleId, userId }: { roleId: string | string; userId: string }): Promise<Record<string, unknown> & Record<string, unknown>> {
    return this.client.delete<Record<string, unknown> & Record<string, unknown>>(this.buildPath('users', userId, 'roles', roleId));
  }

  /**
   * Get User Role Endpoint
   * Get a specific user role by user_id and role_id.
   */
  async getUserRoleEndpointUserRolesUsersUserIdRolesRoleIdGet({ roleId, userId }: { roleId: string | string; userId: string }): Promise<UserRoleGet> {
    return this.client.get<UserRoleGet>(this.buildPath('users', userId, 'roles', roleId));
  }
}
