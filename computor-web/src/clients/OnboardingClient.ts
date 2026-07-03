/**
 * Hand-written client for the public onboarding endpoints.
 *
 * A controlled door establishes a Keycloak login (open self-registration is
 * disabled). The endpoint does not set a session — after a successful call the
 * user must sign in via Keycloak SSO with the password they just chose.
 *
 *   POST /invites/{token}/accept   — invite token is the authorization proof
 *
 * Hand-written (not generated) because the corresponding backend models are
 * public-onboarding specific and the generated InvitesClient is out of date.
 */

import { APIClient, apiClient } from 'api/client';

export interface InviteAcceptBody {
  given_name: string;
  family_name: string;
  email: string;
  /** Password to set for Keycloak login. Complexity is enforced by Keycloak. */
  password: string;
}

export interface InviteAcceptResult {
  user_id: string;
  email: string;
}

export class OnboardingClient {
  private readonly client: APIClient;

  constructor(client: APIClient = apiClient) {
    this.client = client;
  }

  /** Accept an invite: provisions the Keycloak login, then the user signs in via SSO. */
  async acceptInvite(token: string, body: InviteAcceptBody): Promise<InviteAcceptResult> {
    return this.client.post<InviteAcceptResult>(
      `/invites/${encodeURIComponent(token)}/accept`,
      body,
    );
  }
}
