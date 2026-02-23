/**
 * Auto-generated client for ExtensionsClient.
 * Endpoint: /extensions
 */

import type { ExtensionMetadata, ExtensionPublishResponse, ExtensionVersionDetail, ExtensionVersionListResponse, ExtensionVersionYankRequest } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ExtensionsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/extensions');
  }

  /**
   * List Extensions
   */
  async listExtensionsExtensionsGet({ limit, offset, userId }: { limit?: number; offset?: number; userId?: string | null }): Promise<string[]> {
    const queryParams: Record<string, unknown> = {
      limit,
      offset,
      user_id: userId,
    };
    return this.client.get<string[]>(this.basePath, { params: queryParams });
  }

  /**
   * Get Extension Metadata
   */
  async getExtensionMetadataExtensionsExtensionIdentityGet({ extensionIdentity, userId }: { extensionIdentity: string; userId?: string | null }): Promise<ExtensionMetadata> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<ExtensionMetadata>(this.buildPath(extensionIdentity), { params: queryParams });
  }

  /**
   * Download Extension
   */
  async downloadExtensionExtensionsExtensionIdentityDownloadGet({ extensionIdentity, userId, version }: { extensionIdentity: string; userId?: string | null; version?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
      version,
    };
    return this.client.get<void>(this.buildPath(extensionIdentity, 'download'), { params: queryParams });
  }

  /**
   * List Extension Versions
   */
  async listExtensionVersionsExtensionsExtensionIdentityVersionsGet({ extensionIdentity, cursor, includeYanked, limit, userId }: { extensionIdentity: string; cursor?: string | null; includeYanked?: boolean; limit?: number; userId?: string | null }): Promise<ExtensionVersionListResponse> {
    const queryParams: Record<string, unknown> = {
      cursor,
      include_yanked: includeYanked,
      limit,
      user_id: userId,
    };
    return this.client.get<ExtensionVersionListResponse>(this.buildPath(extensionIdentity, 'versions'), { params: queryParams });
  }

  /**
   * Publish Extension Version
   */
  async publishExtensionVersionExtensionsExtensionIdentityVersionsPost({ extensionIdentity, userId }: { extensionIdentity: string; userId?: string | null }): Promise<ExtensionPublishResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<ExtensionPublishResponse>(this.buildPath(extensionIdentity, 'versions'), { params: queryParams });
  }

  /**
   * Update Extension Version
   */
  async updateExtensionVersionExtensionsExtensionIdentityVersionsVersionPatch({ extensionIdentity, version, userId, body }: { extensionIdentity: string; version: string; userId?: string | null; body: ExtensionVersionYankRequest }): Promise<ExtensionVersionDetail> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<ExtensionVersionDetail>(this.buildPath(extensionIdentity, 'versions', version), body, { params: queryParams });
  }
}
