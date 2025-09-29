/**
 * Auto-generated client for SubmissionGroupGradingInterface.
 * Endpoint: /submission-group-gradings
 */

import type { SubmissionGroupGradingCreate, SubmissionGroupGradingGet, SubmissionGroupGradingList, SubmissionGroupGradingQuery, SubmissionGroupGradingUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class SubmissionGroupGradingClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/submission-group-gradings');
  }

  async create(payload: SubmissionGroupGradingCreate): Promise<SubmissionGroupGradingGet> {
    return this.client.post<SubmissionGroupGradingGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<SubmissionGroupGradingGet> {
    return this.client.get<SubmissionGroupGradingGet>(this.buildPath(id));
  }

  async list(params?: SubmissionGroupGradingQuery): Promise<SubmissionGroupGradingList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<SubmissionGroupGradingList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: SubmissionGroupGradingUpdate): Promise<SubmissionGroupGradingGet> {
    return this.client.patch<SubmissionGroupGradingGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }
}
