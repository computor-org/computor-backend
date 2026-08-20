/**
 * Auto-generated client for IssueReportsClient.
 * Endpoint: /issue-reports
 */

import type { IssueReportCreated } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class IssueReportsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/issue-reports');
  }

  /**
   * Create Issue Report
   * Create a GitHub issue without exposing GitHub credentials to clients.
   */
  async createIssueReportIssueReportsPost({ userId }: { userId?: string | null }): Promise<IssueReportCreated> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<IssueReportCreated>(this.basePath, { params: queryParams });
  }
}
