/**
 * Auto-generated client for ExampleInterface.
 * Endpoint: /examples
 */

import type { ExampleCreate, ExampleDependencyCreate, ExampleDependencyGet, ExampleDownloadResponse, ExampleGet, ExampleList, ExampleQuery, ExampleUpdate, ExampleUploadRequest, ExampleVersionCreate, ExampleVersionGet, ExampleVersionList } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ExampleClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/examples');
  }

  async create(payload: ExampleCreate): Promise<ExampleGet> {
    return this.client.post<ExampleGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<ExampleGet> {
    return this.client.get<ExampleGet>(this.buildPath(id));
  }

  async list(params?: ExampleQuery): Promise<ExampleList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<ExampleList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: ExampleUpdate): Promise<ExampleGet> {
    return this.client.patch<ExampleGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }

  /**
   * Remove Dependency
   * Remove a dependency.
   */
  async removeDependencyExamplesDependenciesDependencyIdDelete({ dependencyId }: { dependencyId: string }): Promise<void> {
    return this.client.delete<void>(this.buildPath('dependencies', dependencyId));
  }

  /**
   * Download Example Version
   * Download a specific example version from storage, optionally with all dependencies.
   */
  async downloadExampleVersionExamplesDownloadVersionIdGet({ versionId, withDependencies }: { versionId: string; withDependencies?: boolean }): Promise<ExampleDownloadResponse> {
    const queryParams: Record<string, unknown> = {
      with_dependencies: withDependencies,
    };
    return this.client.get<ExampleDownloadResponse>(this.buildPath('download', versionId), { params: queryParams });
  }

  /**
   * Upload Example
   * Upload an example to storage (MinIO).
   */
  async uploadExampleExamplesUploadPost({ body }: { body: ExampleUploadRequest }): Promise<ExampleVersionGet> {
    return this.client.post<ExampleVersionGet>(this.buildPath('upload'), body);
  }

  /**
   * Get Version
   * Get a specific version.
   */
  async getVersionExamplesVersionsVersionIdGet({ versionId }: { versionId: string }): Promise<ExampleVersionGet> {
    return this.client.get<ExampleVersionGet>(this.buildPath('versions', versionId));
  }

  /**
   * Get Example Dependencies
   * Get all dependencies for an example with version constraints.
   */
  async getExampleDependenciesExamplesExampleIdDependenciesGet({ exampleId }: { exampleId: string }): Promise<ExampleDependencyGet[]> {
    return this.client.get<ExampleDependencyGet[]>(this.buildPath(exampleId, 'dependencies'));
  }

  /**
   * Create Example Dependency
   * Create a new dependency relationship between examples.
   */
  async createExampleDependencyExamplesExampleIdDependenciesPost({ exampleId, body }: { exampleId: string; body: ExampleDependencyCreate }): Promise<ExampleDependencyGet> {
    return this.client.post<ExampleDependencyGet>(this.buildPath(exampleId, 'dependencies'), body);
  }

  /**
   * Delete Example Dependency
   * Delete a dependency relationship between examples.
   */
  async deleteExampleDependencyExamplesExampleIdDependenciesDependencyIdDelete({ dependencyId, exampleId }: { dependencyId: string; exampleId: string }): Promise<void> {
    return this.client.delete<void>(this.buildPath(exampleId, 'dependencies', dependencyId));
  }

  /**
   * Download Example Latest
   * Download the latest version of an example from storage, optionally with all dependencies.
   */
  async downloadExampleLatestExamplesExampleIdDownloadGet({ exampleId, withDependencies }: { exampleId: string; withDependencies?: boolean }): Promise<ExampleDownloadResponse> {
    const queryParams: Record<string, unknown> = {
      with_dependencies: withDependencies,
    };
    return this.client.get<ExampleDownloadResponse>(this.buildPath(exampleId, 'download'), { params: queryParams });
  }

  /**
   * List Versions
   * List all versions of an example.
   */
  async listVersionsExamplesExampleIdVersionsGet({ exampleId, limit, skip, versionTag }: { exampleId: string; limit?: number | null; skip?: number | null; versionTag?: string | null }): Promise<ExampleVersionList[]> {
    const queryParams: Record<string, unknown> = {
      limit,
      skip,
      version_tag: versionTag,
    };
    return this.client.get<ExampleVersionList[]>(this.buildPath(exampleId, 'versions'), { params: queryParams });
  }

  /**
   * Create Version
   * Create a new version for an example.
   */
  async createVersionExamplesExampleIdVersionsPost({ exampleId, body }: { exampleId: string; body: ExampleVersionCreate }): Promise<ExampleVersionGet> {
    return this.client.post<ExampleVersionGet>(this.buildPath(exampleId, 'versions'), body);
  }
}
