/**
 * Auto-generated client for SubmissionsClient.
 * Endpoint: /submissions
 */

import type { SubmissionUploadResponseModel } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class SubmissionsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/submissions');
  }

  /**
   * List Submissions
   * List submission artifacts with optional filtering.
   */
  async listSubmissionsSubmissionsGet({ args, kwds }: { args: string | number | boolean; kwds: string | number | boolean }): Promise<unknown[]> {
    const queryParams: Record<string, unknown> = {
      args,
      kwds,
    };
    return this.client.get<unknown[]>(this.basePath, { params: queryParams });
  }

  /**
   * Upload Submission
   * Upload a submission file to MinIO and create a matching Result record.
   */
  async uploadSubmissionSubmissionsPost(): Promise<SubmissionUploadResponseModel> {
    return this.client.post<SubmissionUploadResponseModel>(this.basePath);
  }
}
