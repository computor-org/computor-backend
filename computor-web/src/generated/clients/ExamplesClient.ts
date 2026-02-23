/**
 * Auto-generated client for ExamplesClient.
 * Endpoint: /examples
 */

import type { ExampleBulkDeleteResult, ExampleDependencyCreate, ExampleDependencyGet, ExampleDownloadResponse, ExampleGet, ExampleList, ExampleUploadRequest, ExampleVersionCreate, ExampleVersionGet, ExampleVersionList, ForceLevel } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ExamplesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/examples');
  }

  /**
   * List Examples
   * List all examples.
   */
  async listExamplesExamplesGet({ category, id, identifier, limit, repositoryId, search, skip, title, userId }: { category?: string | null; id?: string | null; identifier?: string | null; limit?: number | null; repositoryId?: string | null; search?: string | null; skip?: number | null; title?: string | null; userId?: string | null }): Promise<ExampleList[]> {
    const queryParams: Record<string, unknown> = {
      category,
      id,
      identifier,
      limit,
      repository_id: repositoryId,
      search,
      skip,
      title,
      user_id: userId,
    };
    return this.client.get<ExampleList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Delete examples by identifier prefix pattern
   * Delete examples matching an identifier pattern.
   * Pattern uses Ltree matching with * wildcard:
   * - "itpcp.progphys.py.*" matches all examples under itpcp.progphys.py
   * - "itpcp.*" matches all examples under itpcp
   * Force levels for handling deployments:
   * - "none" (default): Blocks if any active deployments exist
   * - "old": Allows deletion if deployments are only in archived courses
   * - "all": Deletes even if actively deployed (orphans deployments)
   * **WARNING**: This is a destructive operation. Use dry_run=true to preview.
   */
  async deleteExamplesByPatternEndpointExamplesByPatternDelete({ dryRun, forceLevel, identifierPattern, repositoryId, userId }: { dryRun?: boolean; forceLevel?: ForceLevel; identifierPattern: string; repositoryId?: string; userId?: string | null }): Promise<ExampleBulkDeleteResult> {
    const queryParams: Record<string, unknown> = {
      dry_run: dryRun,
      force_level: forceLevel,
      identifier_pattern: identifierPattern,
      repository_id: repositoryId,
      user_id: userId,
    };
    return this.client.delete<ExampleBulkDeleteResult>(this.buildPath('by-pattern'), { params: queryParams });
  }

  /**
   * Remove Dependency
   * Remove a dependency.
   */
  async removeDependencyExamplesDependenciesDependencyIdDelete({ dependencyId, userId }: { dependencyId: string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath('dependencies', dependencyId), { params: queryParams });
  }

  /**
   * Download Example Version
   * Download a specific example version from storage, optionally with all dependencies.
   */
  async downloadExampleVersionExamplesDownloadVersionIdGet({ versionId, userId, withDependencies }: { versionId: string; userId?: string | null; withDependencies?: boolean }): Promise<ExampleDownloadResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
      with_dependencies: withDependencies,
    };
    return this.client.get<ExampleDownloadResponse>(this.buildPath('download', versionId), { params: queryParams });
  }

  /**
   * Upload Example
   * Upload an example to storage (MinIO).
   */
  async uploadExampleExamplesUploadPost({ userId, body }: { userId?: string | null; body: ExampleUploadRequest }): Promise<ExampleVersionGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<ExampleVersionGet>(this.buildPath('upload'), body, { params: queryParams });
  }

  /**
   * Get Version
   * Get a specific version.
   */
  async getVersionExamplesVersionsVersionIdGet({ versionId, userId }: { versionId: string; userId?: string | null }): Promise<ExampleVersionGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<ExampleVersionGet>(this.buildPath('versions', versionId), { params: queryParams });
  }

  /**
   * Get Example
   * Get a specific example.
   */
  async getExampleExamplesExampleIdGet({ exampleId, userId }: { exampleId: string; userId?: string | null }): Promise<ExampleGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<ExampleGet>(this.buildPath(exampleId), { params: queryParams });
  }

  /**
   * Get Example Dependencies
   * Get all dependencies for an example with version constraints.
   */
  async getExampleDependenciesExamplesExampleIdDependenciesGet({ exampleId, userId }: { exampleId: string; userId?: string | null }): Promise<ExampleDependencyGet[]> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<ExampleDependencyGet[]>(this.buildPath(exampleId, 'dependencies'), { params: queryParams });
  }

  /**
   * Create Example Dependency
   * Create a new dependency relationship between examples.
   */
  async createExampleDependencyExamplesExampleIdDependenciesPost({ exampleId, userId, body }: { exampleId: string; userId?: string | null; body: ExampleDependencyCreate }): Promise<ExampleDependencyGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<ExampleDependencyGet>(this.buildPath(exampleId, 'dependencies'), body, { params: queryParams });
  }

  /**
   * Delete Example Dependency
   * Delete a dependency relationship between examples.
   */
  async deleteExampleDependencyExamplesExampleIdDependenciesDependencyIdDelete({ dependencyId, exampleId, userId }: { dependencyId: string; exampleId: string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(exampleId, 'dependencies', dependencyId), { params: queryParams });
  }

  /**
   * Download Example Latest
   * Download the latest version of an example from storage, optionally with all dependencies.
   */
  async downloadExampleLatestExamplesExampleIdDownloadGet({ exampleId, userId, withDependencies }: { exampleId: string; userId?: string | null; withDependencies?: boolean }): Promise<ExampleDownloadResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
      with_dependencies: withDependencies,
    };
    return this.client.get<ExampleDownloadResponse>(this.buildPath(exampleId, 'download'), { params: queryParams });
  }

  /**
   * List Versions
   * List all versions of an example.
   */
  async listVersionsExamplesExampleIdVersionsGet({ exampleId, limit, skip, userId, versionTag }: { exampleId: string; limit?: number | null; skip?: number | null; userId?: string | null; versionTag?: string | null }): Promise<ExampleVersionList[]> {
    const queryParams: Record<string, unknown> = {
      limit,
      skip,
      user_id: userId,
      version_tag: versionTag,
    };
    return this.client.get<ExampleVersionList[]>(this.buildPath(exampleId, 'versions'), { params: queryParams });
  }

  /**
   * Create Version
   * Create a new version for an example.
   */
  async createVersionExamplesExampleIdVersionsPost({ exampleId, userId, body }: { exampleId: string; userId?: string | null; body: ExampleVersionCreate }): Promise<ExampleVersionGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<ExampleVersionGet>(this.buildPath(exampleId, 'versions'), body, { params: queryParams });
  }
}
