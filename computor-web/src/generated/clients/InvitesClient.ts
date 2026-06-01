/**
 * Auto-generated client for InvitesClient.
 * Endpoint: /invites
 */

import type { InviteAccept, InviteLinkPublic } from 'types/generated';
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
   */
  async acceptInviteInvitesTokenAcceptPost({ token, userId, body }: { token: string; userId?: string | null; body: InviteAccept }): Promise<Record<string, unknown> & Record<string, unknown>> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<Record<string, unknown> & Record<string, unknown>>(this.buildPath(token, 'accept'), body, { params: queryParams });
  }
}
