/**
 * Auto-generated client for CourseMemberCommentsClient.
 * Endpoint: /course-member-comments
 */

import type { CommentCreate, CommentUpdate, CourseMemberCommentList } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseMemberCommentsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-member-comments');
  }

  /**
   * List Comments
   * List comments accessible to the user (optionally filtered by course_member_id).
   */
  async listCommentsCourseMemberCommentsGet({ courseMemberId, id, limit, skip, transmitterId, userId }: { courseMemberId?: string | null; id?: string | null; limit?: number | null; skip?: number | null; transmitterId?: string | null; userId?: string | null }): Promise<CourseMemberCommentList[]> {
    const queryParams: Record<string, unknown> = {
      course_member_id: courseMemberId,
      id,
      limit,
      skip,
      transmitter_id: transmitterId,
      user_id: userId,
    };
    return this.client.get<CourseMemberCommentList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Comment
   * Create a comment for a course member.
   */
  async createCommentCourseMemberCommentsPost({ userId, body }: { userId?: string | null; body: CommentCreate }): Promise<CourseMemberCommentList[]> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseMemberCommentList[]>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Comment
   * Delete a course member comment.
   */
  async deleteCommentCourseMemberCommentsCourseMemberCommentIdDelete({ courseMemberCommentId, userId }: { courseMemberCommentId: string | string; userId?: string | null }): Promise<CourseMemberCommentList[]> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<CourseMemberCommentList[]>(this.buildPath(courseMemberCommentId), { params: queryParams });
  }

  /**
   * Update Comment
   * Update a course member comment.
   */
  async updateCommentCourseMemberCommentsCourseMemberCommentIdPatch({ courseMemberCommentId, userId, body }: { courseMemberCommentId: string | string; userId?: string | null; body: CommentUpdate }): Promise<CourseMemberCommentList[]> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<CourseMemberCommentList[]>(this.buildPath(courseMemberCommentId), body, { params: queryParams });
  }
}
