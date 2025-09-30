/**
 * Auto-generated client for MessageInterface.
 * Endpoint: /messages
 */

import type { MessageCreate, MessageGet, MessageList, MessageQuery, MessageUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class MessageClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/messages');
  }

  async create(payload: MessageCreate): Promise<MessageGet> {
    return this.client.post<MessageGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<MessageGet> {
    return this.client.get<MessageGet>(this.buildPath(id));
  }

  async list(params?: MessageQuery): Promise<MessageList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<MessageList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: MessageUpdate): Promise<MessageGet> {
    return this.client.patch<MessageGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }

  async archive(id: string | number): Promise<void> {
    await this.client.patch<void>(this.buildPath(id, 'archive'));
  }

  /**
   * Mark Message Read
   */
  async markMessageReadMessagesIdReadsPost({ id }: { id: string | string }): Promise<void> {
    return this.client.post<void>(this.buildPath(id, 'reads'));
  }

  /**
   * Mark Message Unread
   */
  async markMessageUnreadMessagesIdReadsDelete({ id }: { id: string | string }): Promise<void> {
    return this.client.delete<void>(this.buildPath(id, 'reads'));
  }
}
