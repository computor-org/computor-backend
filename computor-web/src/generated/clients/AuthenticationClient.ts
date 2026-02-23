/**
 * Auto-generated client for AuthenticationClient.
 * Endpoint: /password
 */

import type { AdminResetPasswordRequest, AdminSetPasswordRequest, ChangePasswordRequest, PasswordOperationResponse, PasswordStatusResponse, SetPasswordRequest, UserManagerResetPasswordRequest } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class AuthenticationClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/password');
  }

  /**
   * Admin Reset Password
   * Admin endpoint to invalidate user's password and require reset.
   * This does NOT set a new password, it:
   * 1. Marks password as requiring reset
   * 2. User must use password reset flow or admin must set new password
   * Requires admin privileges.
   */
  async adminResetPasswordPasswordAdminResetPost({ userId, body }: { userId?: string | null; body: AdminResetPasswordRequest }): Promise<PasswordOperationResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<PasswordOperationResponse>(this.buildPath('admin', 'reset'), body, { params: queryParams });
  }

  /**
   * Admin Set Password
   * Admin endpoint to set another user's password.
   * Requires admin privileges.
   * Optionally can force user to change password on next login.
   */
  async adminSetPasswordPasswordAdminSetPost({ userId, body }: { userId?: string | null; body: AdminSetPasswordRequest }): Promise<PasswordOperationResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<PasswordOperationResponse>(this.buildPath('admin', 'set'), body, { params: queryParams });
  }

  /**
   * Admin Get User Password Status
   * Admin endpoint to check password status for any user.
   * Requires admin privileges.
   */
  async adminGetUserPasswordStatusPasswordAdminStatusUsernameGet({ username, userId }: { username: string; userId?: string | null }): Promise<PasswordStatusResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<PasswordStatusResponse>(this.buildPath('admin', 'status', username), { params: queryParams });
  }

  /**
   * Change Password
   * Change user's own password.
   * Requires current password for verification.
   * User must know their current password.
   */
  async changePasswordPasswordChangePost({ userId, body }: { userId?: string | null; body: ChangePasswordRequest }): Promise<PasswordOperationResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<PasswordOperationResponse>(this.buildPath('change'), body, { params: queryParams });
  }

  /**
   * User Manager Reset Password
   * User manager endpoint to reset a user's password to NULL.
   * This endpoint:
   * 1. Sets the user's password to NULL (no password)
   * 2. Sets password_reset_required to True
   * 3. User must then set a new password via /password/set (with GitLab PAT or other method)
   * Security requirements:
   * - User must have _user_manager role OR be an admin
   * - User manager must provide their own password for verification
   * - Critical operation - requires password confirmation
   * Requires _user_manager role or admin privileges.
   */
  async userManagerResetPasswordPasswordResetPost({ userId, body }: { userId?: string | null; body: UserManagerResetPasswordRequest }): Promise<PasswordOperationResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<PasswordOperationResponse>(this.buildPath('reset'), body, { params: queryParams });
  }

  /**
   * Set Initial Password
   * Set password for first time or after admin reset.
   * Authentication Methods:
   * 1. Bearer token (user already authenticated)
   * 2. Provider authentication (e.g., GitLab PAT for users without password)
   * Use this endpoint when:
   * - User logging in for first time (password_reset_required = true)
   * - Admin reset user's password
   * - User has no password set
   * This endpoint does NOT require old password.
   * Security Note:
   * - GitLab PAT is only used for verification, NEVER stored (GDPR/DSGVO compliant)
   */
  async setInitialPasswordPasswordSetPost({ userId, body }: { userId?: string | null; body: SetPasswordRequest }): Promise<PasswordOperationResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<PasswordOperationResponse>(this.buildPath('set'), body, { params: queryParams });
  }

  /**
   * Get Password Status
   * Get password status for current user.
   * Returns information about password state:
   * - Whether password is set
   * - Whether password reset is required
   * - Type of password (Argon2, legacy encrypted, or none)
   */
  async getPasswordStatusPasswordStatusGet({ userId }: { userId?: string | null }): Promise<PasswordStatusResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<PasswordStatusResponse>(this.buildPath('status'), { params: queryParams });
  }
}
