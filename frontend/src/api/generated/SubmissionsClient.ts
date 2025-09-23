/**
 * Auto-generated client for SubmissionsClient.
 * Endpoint: /submissions
 */

import type { SubmissionListItem, SubmissionUploadResponseModel, TaskStatus } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class SubmissionsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/submissions');
  }

  /**
   * List Submissions
   * List manual submission results with optional filtering.
   */
  async listSubmissionsSubmissionsGet({ skip, limit, id, submit, courseMemberId, courseSubmissionGroupId, courseContentId, executionBackendId, testSystemId, versionIdentifier, referenceVersionIdentifier, status }: { skip?: number | null; limit?: number | null; id?: string | null; submit?: boolean | null; courseMemberId?: string | null; courseSubmissionGroupId?: string | null; courseContentId?: string | null; executionBackendId?: string | null; testSystemId?: string | null; versionIdentifier?: string | null; referenceVersionIdentifier?: string | null; status?: TaskStatus | null }): Promise<SubmissionListItem[]> {
    const queryParams: Record<string, unknown> = {
      skip,
      limit,
      id,
      submit,
      course_member_id: courseMemberId,
      course_submission_group_id: courseSubmissionGroupId,
      course_content_id: courseContentId,
      execution_backend_id: executionBackendId,
      test_system_id: testSystemId,
      version_identifier: versionIdentifier,
      reference_version_identifier: referenceVersionIdentifier,
      status,
    };
    return this.client.get<SubmissionListItem[]>(this.basePath, { params: queryParams });
  }

  /**
   * Upload Submission
   * Upload a submission file to MinIO and create a matching Result record.
   */
  async uploadSubmissionSubmissionsPost(): Promise<SubmissionUploadResponseModel> {
    return this.client.post<SubmissionUploadResponseModel>(this.basePath);
  }
}
