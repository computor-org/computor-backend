/**
 * Auto-generated client for ServicesClient.
 * Endpoint: /service-accounts
 */

import type { ServiceCreate, ServiceGet, ServiceUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ServicesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/service-accounts');
  }

  /**
   * List Services Endpoint
   * List all service accounts with optional filtering.
   */
  async listServicesEndpointServiceAccountsGet({ enabled, id, limit, serviceTypeId, skip, slug, userId }: { enabled?: boolean | null; id?: string | null; limit?: number | null; serviceTypeId?: string | null; skip?: number | null; slug?: string | null; userId?: string | null }): Promise<ServiceGet[]> {
    const queryParams: Record<string, unknown> = {
      enabled,
      id,
      limit,
      service_type_id: serviceTypeId,
      skip,
      slug,
      user_id: userId,
    };
    return this.client.get<ServiceGet[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Service Endpoint
   * Create a new service account.
   */
  async createServiceEndpointServiceAccountsPost({ userId, body }: { userId?: string | null; body: ServiceCreate }): Promise<ServiceGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<ServiceGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Get Service Me
   * Get the authenticated service account's configuration.
   * This endpoint is designed for Temporal workers and other services
   * to fetch their configuration on startup using their API token.
   * Requires authentication with a service account (is_service=true).
   * Returns:
   * ServiceGet: The service's configuration including config dict, service_type_path, etc.
   * Raises:
   * 403: If the authenticated user is not a service account
   * 404: If the service record is not found for the user
   */
  async getServiceMeServiceAccountsMeGet({ userId }: { userId?: string | null }): Promise<ServiceGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<ServiceGet>(this.buildPath('me'), { params: queryParams });
  }

  /**
   * Delete Service Endpoint
   * Delete (archive) a service account.
   */
  async deleteServiceEndpointServiceAccountsServiceIdDelete({ serviceId, userId }: { serviceId: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(serviceId), { params: queryParams });
  }

  /**
   * Get Service Endpoint
   * Get service account details by ID.
   */
  async getServiceEndpointServiceAccountsServiceIdGet({ serviceId, userId }: { serviceId: string | string; userId?: string | null }): Promise<ServiceGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<ServiceGet>(this.buildPath(serviceId), { params: queryParams });
  }

  /**
   * Update Service Endpoint
   * Update service account details.
   */
  async updateServiceEndpointServiceAccountsServiceIdPatch({ serviceId, userId, body }: { serviceId: string | string; userId?: string | null; body: ServiceUpdate }): Promise<ServiceGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<ServiceGet>(this.buildPath(serviceId), body, { params: queryParams });
  }

  /**
   * Service Heartbeat Endpoint
   * Update service last_seen_at timestamp (heartbeat).
   */
  async serviceHeartbeatEndpointServiceAccountsServiceIdHeartbeatPut({ serviceId, userId }: { serviceId: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.put<void>(this.buildPath(serviceId, 'heartbeat'), { params: queryParams });
  }
}
