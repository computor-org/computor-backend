/**
 * Auto-generated client for ExtensionsGettingStartedClient.
 * Endpoint: /extensions-getting-started
 */

import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ExtensionsGettingStartedClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/extensions-getting-started');
  }

  /**
   * Get Getting Started Url
   * Public endpoint to get extension getting started guide URL.
   * This endpoint requires no authentication and returns the URL
   * specified in the EXTENSION_GETTING_STARTED_URL environment variable.
   */
  async getGettingStartedUrlExtensionsGettingStartedGet(): Promise<string> {
    return this.client.get<string>(this.basePath);
  }
}
