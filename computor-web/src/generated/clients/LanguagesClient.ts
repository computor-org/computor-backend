/**
 * Auto-generated client for LanguagesClient.
 * Endpoint: /languages
 */

import type { LanguageGet, LanguageList } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class LanguagesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/languages');
  }

  /**
   * List Languages
   */
  async listLanguagesLanguagesGet({ code, limit, name, nativeName, skip, userId }: { code?: string | null; limit?: number | null; name?: string | null; nativeName?: string | null; skip?: number | null; userId?: string | null }): Promise<LanguageList[]> {
    const queryParams: Record<string, unknown> = {
      code,
      limit,
      name,
      native_name: nativeName,
      skip,
      user_id: userId,
    };
    return this.client.get<LanguageList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Get Languages
   */
  async getLanguagesLanguagesIdGet({ id, userId }: { id: string; userId?: string | null }): Promise<LanguageGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<LanguageGet>(this.buildPath(id), { params: queryParams });
  }
}
