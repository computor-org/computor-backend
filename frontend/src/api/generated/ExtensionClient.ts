/**
 * Auto-generated client for ExtensionInterface.
 * Endpoint: /extensions
 */

import type { ExtensionMetadata, ExtensionPublishRequest, ExtensionPublishResponse, ExtensionVersionDetail, ExtensionVersionListItem, ExtensionVersionListResponse, ExtensionVersionYankRequest } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ExtensionClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/extensions');
  }

  async create(payload: ExtensionPublishRequest): Promise<ExtensionMetadata> {
    return this.client.post<ExtensionMetadata>(this.basePath, payload);
  }

  async get(id: string | number): Promise<ExtensionMetadata> {
    return this.client.get<ExtensionMetadata>(this.buildPath(id));
  }

  async list(params?: Record<string, unknown>): Promise<ExtensionVersionListItem[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<ExtensionVersionListItem[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: ExtensionVersionYankRequest): Promise<ExtensionMetadata> {
    return this.client.patch<ExtensionMetadata>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }

  /**
   * Download Extension
   */
  async downloadExtensionExtensionsExtensionIdentityDownloadGet({ extensionIdentity, version }: { extensionIdentity: string; version?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      version,
    };
    return this.client.get<void>(this.buildPath(extensionIdentity, 'download'), { params: queryParams });
  }

  /**
   * List Extension Versions
   */
  async listExtensionVersionsExtensionsExtensionIdentityVersionsGet({ extensionIdentity, cursor, includeYanked, limit }: { extensionIdentity: string; cursor?: string | null; includeYanked?: boolean; limit?: number }): Promise<ExtensionVersionListResponse> {
    const queryParams: Record<string, unknown> = {
      cursor,
      include_yanked: includeYanked,
      limit,
    };
    return this.client.get<ExtensionVersionListResponse>(this.buildPath(extensionIdentity, 'versions'), { params: queryParams });
  }

  /**
   * Publish Extension Version
   */
  async publishExtensionVersionExtensionsExtensionIdentityVersionsPost({ extensionIdentity }: { extensionIdentity: string }): Promise<ExtensionPublishResponse> {
    return this.client.post<ExtensionPublishResponse>(this.buildPath(extensionIdentity, 'versions'));
  }

  /**
   * Update Extension Version
   */
  async updateExtensionVersionExtensionsExtensionIdentityVersionsVersionPatch({ extensionIdentity, version, body }: { extensionIdentity: string; version: string; body: ExtensionVersionYankRequest }): Promise<ExtensionVersionDetail> {
    return this.client.patch<ExtensionVersionDetail>(this.buildPath(extensionIdentity, 'versions', version), body);
  }
}
