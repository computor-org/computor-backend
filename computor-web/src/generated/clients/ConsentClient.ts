/**
 * Auto-generated client for ConsentClient.
 * Endpoint: /consent
 */

import type { ConsentCreate, ConsentStatusGet, PolicyTextGet, PolicyVersionCreate, PolicyVersionGet } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ConsentClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/consent');
  }

  /**
   * Give Consent
   * Record the caller's consent for the current policy version.
   * Captures ip/user-agent as proof of consent. Idempotent (partial unique
   * index on active consents). Refreshes the middleware's Redis gate cache so
   * the user can access the API immediately without re-login.
   */
  async giveConsentConsentPost({ userId, body }: { userId?: string | null; body: ConsentCreate }): Promise<ConsentStatusGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<ConsentStatusGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Get Policy Text
   * Current policy version + Markdown notice text, with language fallback.
   */
  async getPolicyTextConsentPolicyGet({ lang, userId }: { lang?: string | null; userId?: string | null }): Promise<PolicyTextGet> {
    const queryParams: Record<string, unknown> = {
      lang,
      user_id: userId,
    };
    return this.client.get<PolicyTextGet>(this.buildPath('policy'), { params: queryParams });
  }

  /**
   * List Policy Versions
   * List all policy versions (admin).
   */
  async listPolicyVersionsConsentPolicyVersionsGet({ userId }: { userId?: string | null }): Promise<PolicyVersionGet[]> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<PolicyVersionGet[]>(this.buildPath('policy-versions'), { params: queryParams });
  }

  /**
   * Publish Policy Version
   * Publish a new policy version (admin).
   * Uploads the Markdown texts to MinIO, inserts the append-only
   * policy_versions row, and invalidates the current-version cache. If
   * effective_from <= now, every user without consent for the new version is
   * re-gated on their next request.
   */
  async publishPolicyVersionConsentPolicyVersionsPost({ userId, body }: { userId?: string | null; body: PolicyVersionCreate }): Promise<PolicyVersionGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<PolicyVersionGet>(this.buildPath('policy-versions'), body, { params: queryParams });
  }

  /**
   * Get Consent Status
   * Current policy version and whether the caller has consented to it.
   */
  async getConsentStatusConsentStatusGet({ userId }: { userId?: string | null }): Promise<ConsentStatusGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<ConsentStatusGet>(this.buildPath('status'), { params: queryParams });
  }

  /**
   * Withdraw Consent
   * Withdraw consent (GDPR Art. 7(3)). The caller is gated again afterwards.
   */
  async withdrawConsentConsentWithdrawPost({ userId }: { userId?: string | null }): Promise<ConsentStatusGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<ConsentStatusGet>(this.buildPath('withdraw'), { params: queryParams });
  }
}
