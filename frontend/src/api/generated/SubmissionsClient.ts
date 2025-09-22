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
   * Upload Submission
   * Upload a submission file to MinIO and create a matching Result record.
   */
  async uploadSubmissionSubmissionsPost(): Promise<SubmissionUploadResponseModel> {
    return this.client.post<SubmissionUploadResponseModel>(this.basePath);
  }
}
