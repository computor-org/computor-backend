/**
 * Hand-written client for the public onboarding endpoints.
 *
 * Two controlled doors establish a Keycloak login (open self-registration is
 * disabled). Neither endpoint sets a session — after a successful call the user
 * must sign in via Keycloak SSO with the password they just chose.
 *
 *   POST /invites/{token}/accept   — invite token is the authorization proof
 *   POST /auth/gitlab/register     — a GitLab PAT is the authorization proof
 *
 * These are hand-written (not generated) because the corresponding backend
 * models are public-onboarding specific and the generated InvitesClient is out
 * of date.
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

export interface GitlabRegisterBody {
  /** GitLab instance URL the PAT was issued on. */
  gitlab_url: string;
  /** GitLab Personal Access Token — used only for verification, never stored. */
  gitlab_pat: string;
  /** Password to set for Keycloak login. */
  new_password: string;
}

export interface GitlabRegisterResult {
  user_id: string;
  email: string;
  /** True if the Keycloak user was created, false if its password was reset. */
  created: boolean;
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

  /** Register/recover via GitLab PAT: provisions or resets the Keycloak login. */
  async registerViaGitlab(body: GitlabRegisterBody): Promise<GitlabRegisterResult> {
    return this.client.post<GitlabRegisterResult>('/auth/gitlab/register', body);
  }
}
