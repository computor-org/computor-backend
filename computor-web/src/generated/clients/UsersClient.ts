/**
 * Auto-generated client for UsersClient.
 * Endpoint: /users
 */

import type { UserBanRequest, UserCreate, UserGet, UserList, UserUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class UsersClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/users');
  }

  /**
   * List Users
   */
  async listUsersUsersGet({ archived, banned, email, familyName, givenName, id, isService, limit, search, skip, userId, username }: { archived?: boolean | null; banned?: boolean | null; email?: string | null; familyName?: string | null; givenName?: string | null; id?: string | null; isService?: boolean | null; limit?: number | null; search?: string | null; skip?: number | null; userId?: string | null; username?: string | null }): Promise<UserList[]> {
    const queryParams: Record<string, unknown> = {
      archived,
      banned,
      email,
      family_name: familyName,
      given_name: givenName,
      id,
      is_service: isService,
      limit,
      search,
      skip,
      user_id: userId,
      username,
    };
    return this.client.get<UserList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Users
   */
  async createUsersUsersPost({ userId, body }: { userId?: string | null; body: UserCreate }): Promise<UserGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<UserGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Users
   */
  async deleteUsersUsersIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Users
   */
  async getUsersUsersIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<UserGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<UserGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Users
   */
  async updateUsersUsersIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: UserUpdate }): Promise<UserGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<UserGet>(this.buildPath(id), body, { params: queryParams });
  }

  /**
   * Route Users
   */
  async routeUsersUsersIdArchivePatch({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<void>(this.buildPath(id, 'archive'), { params: queryParams });
  }

  /**
   * Unarchive Users
   */
  async unarchiveUsersUsersIdUnarchivePatch({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<void>(this.buildPath(id, 'unarchive'), { params: queryParams });
  }

  /**
   * Ban User
   * Ban a user, blocking them from authenticating (admin or _user_manager).
   * Stamps ``banned_at`` (source of truth) plus an optional ``ban_reason`` and
   * sets the Redis kill-switch so any warm auth cache is invalidated at once.
   * Rejects self-bans and bans against ``_admin`` users.
   */
  async banUserUsersUserIdBanPatch({ userId, body }: { userId: string; body?: UserBanRequest | null }): Promise<UserGet> {
    return this.client.patch<UserGet>(this.buildPath(userId, 'ban'), body);
  }

  /**
   * Unban User
   * Lift a user's ban (admin or _user_manager).
   */
  async unbanUserUsersUserIdUnbanPatch({ userId }: { userId: string }): Promise<UserGet> {
    return this.client.patch<UserGet>(this.buildPath(userId, 'unban'));
  }
}
