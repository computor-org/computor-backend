/**
 * Client for support tickets (team mail and problem reports).
 * Endpoint: /support
 *
 * Hand-written, with DTO interfaces mirroring computor_types.support. The list
 * and download calls go through apiFetch directly because the shared APIClient
 * only returns parsed bodies (no X-Total-Count header, no binary payloads).
 */

import { APIClient, apiClient, buildApiError } from 'api/client';
import { API_BASE_URL, apiFetch } from '@/src/utils/apiClient';
import { BaseEndpointClient } from '@/src/generated/clients/baseClient';

export type TicketStatus = 'open' | 'in_progress' | 'waiting' | 'done';
export type TicketPriority = 'low' | 'normal' | 'high';
export type TicketScope = 'unassigned' | 'mine' | 'all';

export interface SupportCapabilities {
  can_view: boolean;
  can_reply: boolean;
  can_manage: boolean;
  can_write_internal: boolean;
  is_admin: boolean;
  team_addresses: string[];
}

export interface TicketUserRef {
  id: string;
  given_name?: string | null;
  family_name?: string | null;
  email?: string | null;
}

export interface SupportAgentRef extends TicketUserRef {
  roles: string[];
}

export interface TicketList {
  id: string;
  number: number;
  subject: string;
  channel: 'mail' | 'web' | 'vscode';
  status: TicketStatus;
  priority: TicketPriority;
  restricted: boolean;
  mailbox_address?: string | null;
  reporter_email?: string | null;
  reporter_name?: string | null;
  reporter_user_id?: string | null;
  assignee?: TicketUserRef | null;
  message_count: number;
  last_message_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TicketAttachment {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  stored: boolean;
}

export interface TicketMessage {
  id: string;
  visibility: 'public' | 'internal';
  direction: 'in' | 'out' | 'note';
  author?: TicketUserRef | null;
  from_address?: string | null;
  from_name?: string | null;
  to: string[];
  cc: string[];
  subject?: string | null;
  text: string;
  /** Sanitised server-side; still only ever shown in a sandboxed iframe. */
  html?: string | null;
  attachments: TicketAttachment[];
  delivery_state?: string | null;
  delivery_error?: string | null;
  created_at: string;
}

export interface TicketEvent {
  id: string;
  kind: string;
  actor?: TicketUserRef | null;
  data: Record<string, unknown>;
  created_at: string;
}

export interface TicketGet extends TicketList {
  messages: TicketMessage[];
  events: TicketEvent[];
}

export interface TicketUpdate {
  status?: TicketStatus;
  priority?: TicketPriority;
  assignee_id?: string;
  unassign?: boolean;
}

export interface TicketMessageCreate {
  content: string;
  internal: boolean;
  from_address?: string;
}

export interface TicketQuery {
  scope?: TicketScope;
  status?: TicketStatus | '';
  search?: string;
  skip?: number;
  limit?: number;
}

export class SupportClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/support');
  }

  capabilities(): Promise<SupportCapabilities> {
    return this.client.get<SupportCapabilities>(this.buildPath('capabilities'));
  }

  agents(): Promise<SupportAgentRef[]> {
    return this.client.get<SupportAgentRef[]>(this.buildPath('agents'));
  }

  /** One page of tickets plus the total from the X-Total-Count header. */
  async list(query: TicketQuery = {}): Promise<{ items: TicketList[]; total: number }> {
    const params = new URLSearchParams();
    if (query.scope) params.set('scope', query.scope);
    if (query.status) params.set('status', query.status);
    if (query.search) params.set('search', query.search);
    if (query.skip !== undefined) params.set('skip', String(query.skip));
    if (query.limit !== undefined) params.set('limit', String(query.limit));
    const qs = params.toString();
    const response = await apiFetch(`${API_BASE_URL}${this.buildPath('tickets')}${qs ? `?${qs}` : ''}`, {
      method: 'GET',
    });
    if (!response.ok) throw await buildApiError(response);
    const items = (await response.json()) as TicketList[];
    const header = Number(response.headers.get('X-Total-Count'));
    return { items, total: Number.isFinite(header) && header > 0 ? header : items.length };
  }

  get(id: string): Promise<TicketGet> {
    return this.client.get<TicketGet>(this.buildPath('tickets', id));
  }

  claim(id: string): Promise<TicketGet> {
    return this.client.post<TicketGet>(this.buildPath('tickets', id, 'claim'));
  }

  update(id: string, body: TicketUpdate): Promise<TicketGet> {
    return this.client.patch<TicketGet>(this.buildPath('tickets', id), body);
  }

  addMessage(id: string, body: TicketMessageCreate): Promise<TicketGet> {
    return this.client.post<TicketGet>(this.buildPath('tickets', id, 'messages'), body);
  }

  retryMessage(id: string, messageId: string): Promise<TicketGet> {
    return this.client.post<TicketGet>(this.buildPath('tickets', id, 'messages', messageId, 'retry'));
  }

  /** Trigger the mail import now (can_manage only; runs asynchronously). */
  importNow(): Promise<unknown> {
    return this.client.post<unknown>(this.buildPath('import'));
  }

  /**
   * Fetch an attachment as an opaque blob. The type is forced to
   * application/octet-stream regardless of what the sender claimed, so the
   * browser can never be coaxed into rendering it.
   */
  async downloadAttachment(ticketId: string, attachmentId: string): Promise<Blob> {
    const response = await apiFetch(
      `${API_BASE_URL}${this.buildPath('tickets', ticketId, 'attachments', attachmentId)}`,
      { method: 'GET' },
    );
    if (!response.ok) throw await buildApiError(response);
    const buffer = await response.arrayBuffer();
    return new Blob([buffer], { type: 'application/octet-stream' });
  }
}

export const supportClient = new SupportClient();
