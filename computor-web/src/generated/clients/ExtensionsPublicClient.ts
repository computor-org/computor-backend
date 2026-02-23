/**
 * Auto-generated client for ExtensionsPublicClient.
 * Endpoint: /extensions-public
 */

import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ExtensionsPublicClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/extensions-public');
  }

  /**
   * Get Public Extension Url
   * Public endpoint to get extension download URL.
   * This endpoint requires no authentication and returns the URL
   * specified in the EXTENSION_PUBLIC_DOWNLOAD_URL environment variable.
   */
  async getPublicExtensionUrlExtensionsPublicGet(): Promise<string> {
    return this.client.get<string>(this.basePath);
  }
}
