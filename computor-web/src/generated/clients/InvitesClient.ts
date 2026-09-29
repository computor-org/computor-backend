/**
 * Auto-generated client for InvitesClient.
 * Endpoint: /invites
 */

import type { InviteAccept, InviteLinkPublic, InviteStatusPublic } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class InvitesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/invites');
  }

  /**
   * Get Invite Public
   * Get invite metadata for the registration page (public, no auth).
   */
  async getInvitePublicInvitesTokenGet({ token, userId }: { token: string; userId?: string | null }): Promise<InviteLinkPublic> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<InviteLinkPublic>(this.buildPath(token), { params: queryParams });
  }

  /**
   * Accept Invite
   * Accept an invite, provision a Keycloak login, and pre-create the user.
   * The invite token is the authorization proof. We create the Keycloak user
   * (with the chosen password) first, then create the computor User. On first
   * SSO login Keycloak links to this pre-created account by email.
   * A pre-provisioned user (admin-created or roster-imported, never signed in)
   * with the same email is ADOPTED instead of rejected — the invite becomes
   * the activation path for the existing row, keeping its memberships and
   * profile (computor-org/issues#382). Only a user with real login evidence
   * blocks the email.
   */
  async acceptInviteInvitesTokenAcceptPost({ token, userId, body }: { token: string; userId?: string | null; body: InviteAccept }): Promise<Record<string, unknown> & Record<string, unknown>> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<Record<string, unknown> & Record<string, unknown>>(this.buildPath(token, 'accept'), body, { params: queryParams });
  }

  /**
   * Get Invite Status
   * Whether a /join code can still be used (public, no auth, rate-limited).
   * Reveals only valid/used/expired/invalid plus whether registration is open
   * at all — never who issued the code, its email restriction or its roles.
   */
  async getInviteStatusInvitesTokenStatusGet({ token, userId }: { token: string; userId?: string | null }): Promise<InviteStatusPublic> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<InviteStatusPublic>(this.buildPath(token, 'status'), { params: queryParams });
  }
}
