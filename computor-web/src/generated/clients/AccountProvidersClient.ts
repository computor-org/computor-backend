/**
 * Client for GET /accounts/providers
 * Returns the list of supported account providers (public, no auth required).
 */

import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export interface AccountProvider {
  id: string;
  display_name: string;
  description: string;
  provider: string;
  type: string;
  field_label: string;
  placeholder: string;
}

export class AccountProvidersClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/accounts/providers');
  }

  async listProviders(): Promise<AccountProvider[]> {
    return this.client.get<AccountProvider[]>(this.basePath);
  }
}
