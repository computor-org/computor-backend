/**
 * Client for the deployment-wide admission limits (#351).
 * Endpoint: /system/limits
 *
 * Hand-written like MaintenanceClient rather than used through the generated
 * SystemClient: the generated names carry the operation-id suffix
 * (`getInstanceLimitsSystemLimitsGet`), which reads badly at every call site.
 * The DTOs themselves are generated and imported.
 */

import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from '@/src/generated/clients/baseClient';
import type { InstanceLimitsGet, InstanceLimitsUpdate } from 'types/generated';

export class InstanceLimitsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/system/limits');
  }

  /** The stored limits plus current usage. Any authenticated user may read. */
  async get(): Promise<InstanceLimitsGet> {
    return this.client.get<InstanceLimitsGet>(this.buildPath());
  }

  /** Replace the stored limits. Admin only. */
  async update(body: InstanceLimitsUpdate): Promise<InstanceLimitsGet> {
    return this.client.put<InstanceLimitsGet>(this.buildPath(), body);
  }
}
