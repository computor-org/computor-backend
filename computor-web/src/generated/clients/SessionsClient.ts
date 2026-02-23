/**
 * Auto-generated client for SessionsClient.
 * Endpoint: /sessions
 */

import type { SessionCreate, SessionGet, SessionList, SessionUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class SessionsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/sessions');
  }

  /**
   * List Sessions
   */
  async listSessionsSessionsGet({ activeOnly, id, ipAddress, limit, sessionId, skip, userId }: { activeOnly?: boolean | null; id?: string | null; ipAddress?: string | null; limit?: number | null; sessionId?: string | null; skip?: number | null; userId?: string | null }): Promise<SessionList[]> {
    const queryParams: Record<string, unknown> = {
      active_only: activeOnly,
      id,
      ip_address: ipAddress,
      limit,
      session_id: sessionId,
      skip,
      user_id: userId,
    };
    return this.client.get<SessionList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Sessions
   */
  async createSessionsSessionsPost({ userId, body }: { userId?: string | null; body: SessionCreate }): Promise<SessionGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<SessionGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Get Session Stats
   * Get session statistics (admin only).
   */
  async getSessionStatsSessionsAdminStatsGet({ userId }: { userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<void>(this.buildPath('admin', 'stats'), { params: queryParams });
  }

  /**
   * List User Sessions Admin
   * List sessions for any user (admin only).
   */
  async listUserSessionsAdminSessionsAdminUsersUserIdGet({ userId, activeOnly }: { userId: string; activeOnly?: boolean }): Promise<SessionGet[]> {
    const queryParams: Record<string, unknown> = {
      active_only: activeOnly,
    };
    return this.client.get<SessionGet[]>(this.buildPath('admin', 'users', userId), { params: queryParams });
  }

  /**
   * Revoke All User Sessions Admin
   * Revoke all sessions for a user (admin only).
   */
  async revokeAllUserSessionsAdminSessionsAdminUsersUserIdAllDelete({ userId, reason }: { userId: string; reason?: string }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      reason,
    };
    return this.client.delete<void>(this.buildPath('admin', 'users', userId, 'all'), { params: queryParams });
  }

  /**
   * Revoke Session Admin
   * Force revoke any session (admin only).
   */
  async revokeSessionAdminSessionsAdminSessionIdDelete({ sessionId, reason, userId }: { sessionId: string; reason?: string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      reason,
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath('admin', sessionId), { params: queryParams });
  }

  /**
   * List My Sessions
   * List all active sessions for the authenticated user.
   * Returns sessions ordered by last activity (most recent first).
   */
  async listMySessionsSessionsMeGet({ userId }: { userId?: string | null }): Promise<SessionList[]> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<SessionList[]>(this.buildPath('me'), { params: queryParams });
  }

  /**
   * Revoke All My Sessions
   * Revoke all sessions for the current user.
   * By default, keeps the current session active. Set include_current=true to logout everywhere.
   */
  async revokeAllMySessionsSessionsMeAllDelete({ includeCurrent, userId }: { includeCurrent?: boolean; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      include_current: includeCurrent,
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath('me', 'all'), { params: queryParams });
  }

  /**
   * Get Current Session
   * Get details of the current session (based on access token).
   */
  async getCurrentSessionSessionsMeCurrentGet({ userId }: { userId?: string | null }): Promise<SessionGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<SessionGet>(this.buildPath('me', 'current'), { params: queryParams });
  }

  /**
   * Revoke My Session
   * Revoke a specific session (remote logout).
   * Use this to logout from another device remotely.
   */
  async revokeMySessionSessionsMeSessionIdDelete({ sessionId, userId }: { sessionId: string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath('me', sessionId), { params: queryParams });
  }

  /**
   * Delete Sessions
   */
  async deleteSessionsSessionsIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Sessions
   */
  async getSessionsSessionsIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<SessionGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<SessionGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Sessions
   */
  async updateSessionsSessionsIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: SessionUpdate }): Promise<SessionGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<SessionGet>(this.buildPath(id), body, { params: queryParams });
  }
}
