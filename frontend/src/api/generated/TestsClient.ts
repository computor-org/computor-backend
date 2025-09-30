/**
 * Auto-generated client for TestsClient.
 * Endpoint: /tests
 */

import type { ResultList, TestCreate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class TestsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/tests');
  }

  /**
   * Create Test Run
   * Create and execute a test for a submission artifact.
   * Ways to specify what to test:
   * 1. Provide artifact_id directly
   * 2. Provide submission_group_id + version_identifier to find specific version
   * 3. Provide submission_group_id only to test the latest submission
   * Tests are executed via Temporal workflows.
   */
  async createTestRunTestsPost({ body }: { body: TestCreate }): Promise<ResultList> {
    return this.client.post<ResultList>(this.basePath, body);
  }

  /**
   * Get Test Status
   * Get the current status of a test execution.
   * Permission rules:
   * - Students can view their own test results (member of submission group)
   * - Tutors and higher roles can view all test results in their courses
   */
  async getTestStatusTestsStatusResultIdGet({ resultId }: { resultId: string }): Promise<void> {
    return this.client.get<void>(this.buildPath('status', resultId));
  }
}
