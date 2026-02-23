/**
 * Auto-generated client for AccountsClient.
 * Endpoint: /accounts
 */

import type { AccountCreate, AccountGet, AccountList, AccountUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class AccountsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/accounts');
  }

  /**
   * List Accounts
   */
  async listAccountsAccountsGet({ id, limit, provider, providerAccountId, skip, type, userId }: { id?: string | null; limit?: number | null; provider?: string | null; providerAccountId?: string | null; skip?: number | null; type?: string | null; userId?: string | null }): Promise<AccountList[]> {
    const queryParams: Record<string, unknown> = {
      id,
      limit,
      provider,
      provider_account_id: providerAccountId,
      skip,
      type,
      user_id: userId,
    };
    return this.client.get<AccountList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Accounts
   */
  async createAccountsAccountsPost({ userId, body }: { userId?: string | null; body: AccountCreate }): Promise<AccountGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<AccountGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Accounts
   */
  async deleteAccountsAccountsIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Accounts
   */
  async getAccountsAccountsIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<AccountGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<AccountGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Accounts
   */
  async updateAccountsAccountsIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: AccountUpdate }): Promise<AccountGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<AccountGet>(this.buildPath(id), body, { params: queryParams });
  }
}
