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
   * Readable by any authenticated user: "the server restarted an hour ago" is
   * the answer to a question every user asks when something breaks under them,
   * and refusing it only makes them ask an admin.
   * The commit is the exception, and is redacted rather than split into a second
   * endpoint — a full SHA names the exact source of a public repository, which
   * describes the deployment rather than serving the user.
   */
  async getInstanceStatusInstanceStatusGet(): Promise<InstanceStatusGet> {
    return this.client.get<InstanceStatusGet>(this.basePath);
  }
}
