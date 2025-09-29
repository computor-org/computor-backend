/**
 * Auto-generated client for ExampleInterface.
 * Endpoint: /examples
 */

import type { ExampleCreate, ExampleGet, ExampleList, ExampleQuery, ExampleUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ExampleClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/examples');
  }

  async create(payload: ExampleCreate): Promise<ExampleGet> {
    return this.client.post<ExampleGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<ExampleGet> {
    return this.client.get<ExampleGet>(this.buildPath(id));
  }

  async list(params?: ExampleQuery): Promise<ExampleList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<ExampleList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: ExampleUpdate): Promise<ExampleGet> {
    return this.client.patch<ExampleGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }
}
