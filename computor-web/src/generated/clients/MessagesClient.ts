/**
 * Auto-generated client for MessagesClient.
 * Endpoint: /messages
 */

import type { MessageCreate, MessageGet, MessageList, MessageUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class MessagesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/messages');
  }

  /**
   * List Messages
   * List messages with read status.
   * Supports filtering by:
   * - unread: True = unread only, False = read only, None = all
   * - created_after/created_before: Datetime boundaries
   * - tags: List of tags in format "scope::value" to filter by (in title)
   * - tags_match_all: True = must match ALL tags, False = match ANY tag
   * - tag_scope: Wildcard scope filter (e.g., "ai" matches any #ai::* tag)
   */
  async listMessagesMessagesGet({ authorId, courseContentId, courseFamilyId, courseGroupId, courseId, courseIdAllMessages, courseMemberId, createdAfter, createdBefore, id, limit, organizationId, parentId, scope, skip, submissionGroupId, tagScope, tags, tagsMatchAll, unread, userId }: { authorId?: string | null; courseContentId?: string | null; courseFamilyId?: string | null; courseGroupId?: string | null; courseId?: string | null; courseIdAllMessages?: boolean | null; courseMemberId?: string | null; createdAfter?: string | null; createdBefore?: string | null; id?: string | null; limit?: number | null; organizationId?: string | null; parentId?: string | null; scope?: 'global' | 'organization' | 'course_family' | 'course' | 'course_content' | 'course_group' | 'submission_group' | 'course_member' | 'user' | null; skip?: number | null; submissionGroupId?: string | null; tagScope?: string | null; tags?: string[] | null; tagsMatchAll?: boolean | null; unread?: boolean | null; userId?: string | null }): Promise<MessageList[]> {
    const queryParams: Record<string, unknown> = {
      author_id: authorId,
      course_content_id: courseContentId,
      course_family_id: courseFamilyId,
      course_group_id: courseGroupId,
      course_id: courseId,
      course_id_all_messages: courseIdAllMessages,
      course_member_id: courseMemberId,
      created_after: createdAfter,
      created_before: createdBefore,
      id,
      limit,
      organization_id: organizationId,
      parent_id: parentId,
      scope,
      skip,
      submission_group_id: submissionGroupId,
      tag_scope: tagScope,
      tags,
      tags_match_all: tagsMatchAll,
      unread,
      user_id: userId,
    };
    return this.client.get<MessageList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Message
   * Create a new message with enforced author and defaults.
   */
  async createMessageMessagesPost({ userId, body }: { userId?: string | null; body: MessageCreate }): Promise<MessageGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<MessageGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Message
   * Soft delete a message (preserves thread structure).
   */
  async deleteMessageMessagesIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Message
   * Get a message with read status.
   */
  async getMessageMessagesIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<MessageGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<MessageGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Message
   * Update a message with audit logging.
   */
  async updateMessageMessagesIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: MessageUpdate }): Promise<MessageGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<MessageGet>(this.buildPath(id), body, { params: queryParams });
  }

  /**
   * Get Message Audit
   * Get audit history for a message (author or admin only).
   */
  async getMessageAuditMessagesIdAuditGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<void>(this.buildPath(id, 'audit'), { params: queryParams });
  }

  /**
   * Mark Message Unread
   * Mark a message as unread.
   */
  async markMessageUnreadMessagesIdReadsDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id, 'reads'), { params: queryParams });
  }

  /**
   * Mark Message Read
   * Mark a message as read.
   */
  async markMessageReadMessagesIdReadsPost({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<void>(this.buildPath(id, 'reads'), { params: queryParams });
  }
}
