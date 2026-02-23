/**
 * Auto-generated client for SubmissionGroupsClient.
 * Endpoint: /submission-groups
 */

import type { JoinTeamRequest, JoinTeamResponse, SubmissionGroupCreate, SubmissionGroupGet, SubmissionGroupList, SubmissionGroupProperties, SubmissionGroupUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class SubmissionGroupsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/submission-groups');
  }

  /**
   * List Submission-Groups
   */
  async listSubmissionGroupsSubmissionGroupsGet({ courseContentId, courseId, displayName, id, limit, maxGroupSize, maxSubmissions, skip, status, userId }: { courseContentId?: string | null; courseId?: string | null; displayName?: string | null; id?: string | null; limit?: number | null; maxGroupSize?: number | null; maxSubmissions?: number | null; skip?: number | null; status?: string | null; userId?: string | null }): Promise<SubmissionGroupList[]> {
    const queryParams: Record<string, unknown> = {
      course_content_id: courseContentId,
      course_id: courseId,
      display_name: displayName,
      id,
      limit,
      max_group_size: maxGroupSize,
      max_submissions: maxSubmissions,
      skip,
      status,
      user_id: userId,
    };
    return this.client.get<SubmissionGroupList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Submission-Groups
   */
  async createSubmissionGroupsSubmissionGroupsPost({ userId, body }: { userId?: string | null; body: SubmissionGroupCreate }): Promise<SubmissionGroupGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<SubmissionGroupGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Submission-Groups
   */
  async deleteSubmissionGroupsSubmissionGroupsIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Submission-Groups
   */
  async getSubmissionGroupsSubmissionGroupsIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<SubmissionGroupGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<SubmissionGroupGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Submission-Groups
   */
  async updateSubmissionGroupsSubmissionGroupsIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: SubmissionGroupUpdate }): Promise<SubmissionGroupGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<SubmissionGroupGet>(this.buildPath(id), body, { params: queryParams });
  }

  /**
   * Join Team
   * Join an existing team.
   * If require_approval is true, the join request will be pending until approved.
   * Otherwise, the user is immediately added to the team.
   */
  async joinTeamSubmissionGroupsSubmissionGroupIdJoinPost({ submissionGroupId, userId, body }: { submissionGroupId: string; userId?: string | null; body: JoinTeamRequest }): Promise<JoinTeamResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<JoinTeamResponse>(this.buildPath(submissionGroupId, 'join'), body, { params: queryParams });
  }
}
