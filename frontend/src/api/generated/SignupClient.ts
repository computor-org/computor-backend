/**
 * Auto-generated client for SignupClient.
 * Endpoint: /signup
 */

import type { GitlabSignup, GitlabSignupResponse } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class SignupClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/signup');
  }

  /**
   * Gitlab Signup
   */
  async gitlabSignupSignupGitlabPost({ body }: { body: GitlabSignup }): Promise<GitlabSignupResponse> {
    return this.client.post<GitlabSignupResponse>(this.buildPath('gitlab'), body);
  }
}
