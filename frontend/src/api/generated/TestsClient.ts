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
   * Create Test For Artifact
   * Create and execute a test for a submission artifact.
   * Tests are executed via Temporal workflows.
   */
  async createTestForArtifactTestsArtifactsArtifactIdTestPost({ artifactId, body }: { artifactId: string; body: TestCreate }): Promise<ResultList> {
    return this.client.post<ResultList>(this.buildPath('artifacts', artifactId, 'test'), body);
  }

  /**
   * Get Test Status
   * Get the current status of a test execution.
   */
  async getTestStatusTestsTestResultsTestIdStatusGet({ testId }: { testId: string }): Promise<void> {
    return this.client.get<void>(this.buildPath('test-results', testId, 'status'));
  }

  /**
   * Create Test Legacy
   * Legacy endpoint for creating tests without an artifact.
   * This creates a temporary artifact and then runs the test.
   * This endpoint is maintained for backwards compatibility but should
   * be replaced with the artifact-based approach.
   */
  async createTestLegacyTestsLegacyPost({ body }: { body: TestCreate }): Promise<ResultList> {
    return this.client.post<ResultList>(this.buildPath('legacy'), body);
  }
}
