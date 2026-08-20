/**
 * Auto-generated client for IssueReportsClient.
 * Endpoint: /issue-reports
 */

import type { IssueReportCreated, IssueReportGet } from 'types/generated';
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

  /**
   * Get Issue Report
   * Resolve a report id to the person who filed it.
   * The GitHub issue names nobody on purpose, so this is the only way back from
   * a report to a reporter — and it is admin-only precisely because that is a
   * step someone should have to take deliberately.
   */
  async getIssueReportIssueReportsReportIdGet({ reportId, userId }: { reportId: string; userId?: string | null }): Promise<IssueReportGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<IssueReportGet>(this.buildPath(reportId), { params: queryParams });
  }
}
