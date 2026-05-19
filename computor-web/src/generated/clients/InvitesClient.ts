/**
 * Client for invite link management endpoints.
 * Admin/user-manager: /admin/invites
 * Public: /invites/{token}
 */

import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export interface InviteLinkCreate {
  email?: string | null;
  max_uses?: number;
  expires_in_days?: number;
  roles?: string[];
  note?: string | null;
}

export interface InviteLinkGet {
  id: string;
  token: string;
  created_by?: string | null;
  email?: string | null;
  max_uses: number;
  use_count: number;
  expires_at: string;
  roles: string[];
  note?: string | null;
  revoked_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface InviteLinkList {
  id: string;
  token: string;
  email?: string | null;
  max_uses: number;
  use_count: number;
  expires_at: string;
  roles: string[];
  note?: string | null;
  revoked_at?: string | null;
  created_at?: string | null;
}

export interface InviteLinkPublic {
  id: string;
  email?: string | null;
  roles: string[];
  expires_at: string;
  note?: string | null;
}

export interface InviteAccept {
  username: string;
  given_name: string;
  family_name: string;
  email: string;
  password: string;
  confirm_password: string;
}

export interface InviteAcceptResponse {
  user_id: string;
  username: string;
  access_token: string;
}

export class InvitesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/admin/invites');
  }

  async createInvite(body: InviteLinkCreate): Promise<InviteLinkGet> {
    return this.client.post<InviteLinkGet>(this.basePath, body);
  }

  async listInvites(): Promise<InviteLinkList[]> {
    return this.client.get<InviteLinkList[]>(this.basePath);
  }

  async getInvite(id: string): Promise<InviteLinkGet> {
    return this.client.get<InviteLinkGet>(this.buildPath(id));
  }

  async revokeInvite(id: string): Promise<void> {
    return this.client.delete<void>(this.buildPath(id));
  }
}

/** Public client (no authentication required) */
export class PublicInvitesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/invites');
  }

  async getInvitePublic(token: string): Promise<InviteLinkPublic> {
    return this.client.get<InviteLinkPublic>(this.buildPath(token));
  }

  async acceptInvite(token: string, body: InviteAccept): Promise<InviteAcceptResponse> {
    return this.client.post<InviteAcceptResponse>(this.buildPath(token, 'accept'), body);
  }
}
