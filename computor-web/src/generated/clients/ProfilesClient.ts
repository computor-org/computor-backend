/**
 * Auto-generated client for ProfilesClient.
 * Endpoint: /profiles
 */

import type { ProfileCreate, ProfileGet, ProfileList, ProfileUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ProfilesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/profiles');
  }

  /**
   * List Profiles Endpoint
   * List profiles - admins/_user_manager see all, users see only their own.
   */
  async listProfilesEndpointProfilesGet({ id, languageCode, limit, nickname, skip, userId }: { id?: string | null; languageCode?: string | null; limit?: number | null; nickname?: string | null; skip?: number | null; userId?: string | null }): Promise<ProfileList[]> {
    const queryParams: Record<string, unknown> = {
      id,
      language_code: languageCode,
      limit,
      nickname,
      skip,
      user_id: userId,
    };
    return this.client.get<ProfileList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Profile Endpoint
   * Create a profile - users can create for themselves, admins/_user_manager can create for anyone.
   */
  async createProfileEndpointProfilesPost({ userId, body }: { userId?: string | null; body: ProfileCreate }): Promise<ProfileGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<ProfileGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Profile Endpoint
   * Delete a profile - users can only delete their own, admins/_user_manager can delete any.
   */
  async deleteProfileEndpointProfilesIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Profile Endpoint
   * Get a profile by ID - users can only get their own, admins/_user_manager can get any.
   */
  async getProfileEndpointProfilesIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<ProfileGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<ProfileGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Profile Endpoint
   * Update a profile - users can only update their own, admins/_user_manager can update any.
   */
  async updateProfileEndpointProfilesIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: ProfileUpdate }): Promise<ProfileGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<ProfileGet>(this.buildPath(id), body, { params: queryParams });
  }
}
