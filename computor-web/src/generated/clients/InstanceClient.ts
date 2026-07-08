/**
 * Auto-generated client for InstanceClient.
 * Endpoint: /instance-info
 */

import type { InstanceInfoGet } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class InstanceClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/instance-info');
  }

  /**
   * Get Instance Info
   * Public navigation URLs for this Computor instance.
   */
  async getInstanceInfoInstanceInfoGet(): Promise<InstanceInfoGet> {
    return this.client.get<InstanceInfoGet>(this.basePath);
  }
}
