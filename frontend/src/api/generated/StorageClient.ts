/**
 * Auto-generated client for StorageInterface.
 * Endpoint: /storage
 */

import type { StorageObjectCreate, StorageObjectGet, StorageObjectList, StorageObjectQuery, StorageObjectUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class StorageClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/storage');
  }

  async create(payload: StorageObjectCreate): Promise<StorageObjectGet> {
    return this.client.post<StorageObjectGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<StorageObjectGet> {
    return this.client.get<StorageObjectGet>(this.buildPath(id));
  }

  async list(params?: StorageObjectQuery): Promise<StorageObjectList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<StorageObjectList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: StorageObjectUpdate): Promise<StorageObjectGet> {
    return this.client.patch<StorageObjectGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }
}
