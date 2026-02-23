/**
 * Auto-generated client for SubmissionGroupMembersClient.
 * Endpoint: /submission-group-members
 */

import type { SubmissionGroupMemberCreate, SubmissionGroupMemberGet, SubmissionGroupMemberList, SubmissionGroupMemberUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class SubmissionGroupMembersClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/submission-group-members');
  }

  /**
   * List Submission-Group-Members
   */
  async listSubmissionGroupMembersSubmissionGroupMembersGet({ courseContentId, courseId, courseMemberId, grading, id, limit, skip, status, submissionGroupId, userId }: { courseContentId?: string | null; courseId?: string | null; courseMemberId?: string | null; grading?: number | null; id?: string | null; limit?: number | null; skip?: number | null; status?: string | null; submissionGroupId?: string | null; userId?: string | null }): Promise<SubmissionGroupMemberList[]> {
    const queryParams: Record<string, unknown> = {
      course_content_id: courseContentId,
      course_id: courseId,
      course_member_id: courseMemberId,
      grading,
      id,
      limit,
      skip,
      status,
      submission_group_id: submissionGroupId,
      user_id: userId,
    };
    return this.client.get<SubmissionGroupMemberList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Submission-Group-Members
   */
  async createSubmissionGroupMembersSubmissionGroupMembersPost({ userId, body }: { userId?: string | null; body: SubmissionGroupMemberCreate }): Promise<SubmissionGroupMemberGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<SubmissionGroupMemberGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Submission-Group-Members
   */
  async deleteSubmissionGroupMembersSubmissionGroupMembersIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Submission-Group-Members
   */
  async getSubmissionGroupMembersSubmissionGroupMembersIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<SubmissionGroupMemberGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<SubmissionGroupMemberGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Submission-Group-Members
   */
  async updateSubmissionGroupMembersSubmissionGroupMembersIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: SubmissionGroupMemberUpdate }): Promise<SubmissionGroupMemberGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<SubmissionGroupMemberGet>(this.buildPath(id), body, { params: queryParams });
  }
}
