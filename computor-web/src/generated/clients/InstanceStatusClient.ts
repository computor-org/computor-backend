/**
 * Auto-generated client for InstanceStatusClient.
 * Endpoint: /instance-status
 */

import type { InstanceStatusGet } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class InstanceStatusClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/instance-status');
  }

  /**
   * Get Instance Status
   * When this API last restarted and what it is running (#350).
   * Admin-only. Nothing here is a secret in itself — a commit hash and two
   * timestamps — but it describes the deployment rather than serving the user,
   * and the operator asking for it is the only one it helps.
   */
  async getInstanceStatusInstanceStatusGet(): Promise<InstanceStatusGet> {
    return this.client.get<InstanceStatusGet>(this.basePath);
  }
}
