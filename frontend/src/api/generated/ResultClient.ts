/**
 * Auto-generated client for ResultInterface.
 * Endpoint: /results
 */

import type { ResultCreate, ResultGet, ResultList, ResultQuery, ResultUpdate, TaskStatus } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ResultClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/results');
  }

  async create(payload: ResultCreate): Promise<ResultGet> {
    return this.client.post<ResultGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<ResultGet> {
    return this.client.get<ResultGet>(this.buildPath(id));
  }

  async list(params?: ResultQuery): Promise<ResultList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<ResultList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: ResultUpdate): Promise<ResultGet> {
    return this.client.patch<ResultGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }

  /**
   * Result Status
   */
  async resultStatusResultsResultIdStatusGet({ resultId }: { resultId: string | string }): Promise<TaskStatus> {
    return this.client.get<TaskStatus>(this.buildPath(resultId, 'status'));
  }
}
