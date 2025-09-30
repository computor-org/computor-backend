/**
 * Auto-generated client for LanguageInterface.
 * Endpoint: /languages
 */

import type { LanguageCreate, LanguageGet, LanguageList, LanguageQuery, LanguageUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class LanguageClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/languages');
  }

  async create(payload: LanguageCreate): Promise<LanguageGet> {
    return this.client.post<LanguageGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<LanguageGet> {
    return this.client.get<LanguageGet>(this.buildPath(id));
  }

  async list(params?: LanguageQuery): Promise<LanguageList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<LanguageList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: LanguageUpdate): Promise<LanguageGet> {
    return this.client.patch<LanguageGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }
}
