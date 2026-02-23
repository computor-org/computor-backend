/**
 * Auto-generated client for ServiceTypesClient.
 * Endpoint: /service-types
 */

import type { ServiceTypeCreate, ServiceTypeGet, ServiceTypeList, ServiceTypeUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ServiceTypesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/service-types');
  }

  /**
   * List Service Types
   * List service types with filtering.
   * Requires: service_type:list permission
   * Query parameters:
   * - path: Exact path match
   * - path_descendant: Get all descendants (e.g., 'testing' returns all testing.*)
   * - path_pattern: Ltree lquery pattern
   * - category: Filter by category
   * - enabled: Filter by enabled status
   * - skip: Pagination offset
   * - limit: Pagination limit
   * Examples:
   * GET /service-types
   * GET /service-types?category=testing
   * GET /service-types?path_descendant=testing
   * GET /service-types?enabled=true
   */
  async listServiceTypesServiceTypesGet({ category, enabled, id, limit, path, pathDescendant, pathPattern, pluginModule, skip, userId }: { category?: string | null; enabled?: boolean | null; id?: string | null; limit?: number | null; path?: string | null; pathDescendant?: string | null; pathPattern?: string | null; pluginModule?: string | null; skip?: number | null; userId?: string | null }): Promise<ServiceTypeList[]> {
    const queryParams: Record<string, unknown> = {
      category,
      enabled,
      id,
      limit,
      path,
      path_descendant: pathDescendant,
      path_pattern: pathPattern,
      plugin_module: pluginModule,
      skip,
      user_id: userId,
    };
    return this.client.get<ServiceTypeList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Service Type
   * Create a new service type.
   * Requires: service_type:create permission
   * Example:
   * POST /service-types
   * {
   * "path": "testing.rust",
   * "name": "Rust Testing System",
   * "description": "Rust code compilation and testing",
   * "category": "testing",
   * "plugin_module": "computor_backend.plugins.testing.rust",
   * "enabled": true
   * }
   */
  async createServiceTypeServiceTypesPost({ userId, body }: { userId?: string | null; body: ServiceTypeCreate }): Promise<ServiceTypeGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<ServiceTypeGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Get Service Type
   * Get a single service type by UUID.
   * Requires: service_type:get permission
   * Example:
   * GET /service-types/123e4567-e89b-12d3-a456-426614174000
   */
  async getServiceTypeServiceTypesEntityIdGet({ entityId, userId }: { entityId: string; userId?: string | null }): Promise<ServiceTypeGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<ServiceTypeGet>(this.buildPath(entityId), { params: queryParams });
  }

  /**
   * Update Service Type
   * Update an existing service type.
   * Requires: service_type:update permission
   * Note: The 'path' field cannot be updated (use id for stable references).
   * Example:
   * PATCH /service-types/123e4567-e89b-12d3-a456-426614174000
   * {
   * "name": "Updated Name",
   * "description": "Updated description",
   * "enabled": false
   * }
   */
  async updateServiceTypeServiceTypesEntityIdPatch({ entityId, userId, body }: { entityId: string; userId?: string | null; body: ServiceTypeUpdate }): Promise<ServiceTypeGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<ServiceTypeGet>(this.buildPath(entityId), body, { params: queryParams });
  }
}
