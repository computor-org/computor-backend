/**
 * Auto-generated client for StorageInterface.
 * Endpoint: /storage
 */

import type { BucketCreate, BucketInfo, PresignedUrlRequest, PresignedUrlResponse, StorageObjectCreate, StorageObjectGet, StorageObjectList, StorageObjectQuery, StorageObjectUpdate, StorageUsageStats } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class StorageClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/storage');
  }

  async create(payload: StorageObjectCreate): Promise<StorageObjectGet> {
    return this.client.post<StorageObjectGet>(this.basePath, payload);
  }

  async get(id: string | number): Promise<StorageObjectGet> {
    return this.client.get<StorageObjectGet>(this.buildPath(id));
  }

  async list(params?: StorageObjectQuery): Promise<StorageObjectList[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<StorageObjectList[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: StorageObjectUpdate): Promise<StorageObjectGet> {
    return this.client.patch<StorageObjectGet>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }

  /**
   * Upload File
   * Upload a file to storage with security validation
   */
  async uploadFileStorageUploadPost(): Promise<StorageObjectGet> {
    return this.client.post<StorageObjectGet>(this.buildPath('upload'));
  }

  /**
   * Download File
   * Download a file from storage
   */
  async downloadFileStorageDownloadObjectKeyGet({ objectKey, bucketName }: { objectKey: string; bucketName?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      bucket_name: bucketName,
    };
    return this.client.get<void>(this.buildPath('download', objectKey), { params: queryParams });
  }

  /**
   * List Objects
   * List objects in storage with optional filtering
   */
  async listObjectsStorageObjectsGet({ skip, limit, bucketName, prefix, contentType, minSize, maxSize }: { skip?: number | null; limit?: number | null; bucketName?: string | null; prefix?: string | null; contentType?: string | null; minSize?: number | null; maxSize?: number | null }): Promise<StorageObjectList[]> {
    const queryParams: Record<string, unknown> = {
      skip,
      limit,
      bucket_name: bucketName,
      prefix,
      content_type: contentType,
      min_size: minSize,
      max_size: maxSize,
    };
    return this.client.get<StorageObjectList[]>(this.buildPath('objects'), { params: queryParams });
  }

  /**
   * Get Object Info
   * Get metadata for a specific object
   */
  async getObjectInfoStorageObjectsObjectKeyGet({ objectKey, bucketName }: { objectKey: string; bucketName?: string | null }): Promise<StorageObjectGet> {
    const queryParams: Record<string, unknown> = {
      bucket_name: bucketName,
    };
    return this.client.get<StorageObjectGet>(this.buildPath('objects', objectKey), { params: queryParams });
  }

  /**
   * Delete Object
   * Delete an object from storage
   */
  async deleteObjectStorageObjectsObjectKeyDelete({ objectKey, bucketName }: { objectKey: string; bucketName?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      bucket_name: bucketName,
    };
    return this.client.delete<void>(this.buildPath('objects', objectKey), { params: queryParams });
  }

  /**
   * Copy Object
   * Copy an object within or between buckets
   */
  async copyObjectStorageCopyPost(): Promise<void> {
    return this.client.post<void>(this.buildPath('copy'));
  }

  /**
   * Generate Presigned Url
   * Generate a presigned URL for direct object access
   */
  async generatePresignedUrlStoragePresignedUrlPost({ body }: { body: PresignedUrlRequest }): Promise<PresignedUrlResponse> {
    return this.client.post<PresignedUrlResponse>(this.buildPath('presigned-url'), body);
  }

  /**
   * List Buckets
   * List all available buckets
   */
  async listBucketsStorageBucketsGet(): Promise<BucketInfo[]> {
    return this.client.get<BucketInfo[]>(this.buildPath('buckets'));
  }

  /**
   * Create Bucket
   * Create a new storage bucket
   */
  async createBucketStorageBucketsPost({ body }: { body: BucketCreate }): Promise<BucketInfo> {
    return this.client.post<BucketInfo>(this.buildPath('buckets'), body);
  }

  /**
   * Delete Bucket
   * Delete a storage bucket
   */
  async deleteBucketStorageBucketsBucketNameDelete({ bucketName, force }: { bucketName: string; force?: boolean }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      force,
    };
    return this.client.delete<void>(this.buildPath('buckets', bucketName), { params: queryParams });
  }

  /**
   * Get Bucket Stats
   * Get usage statistics for a bucket
   */
  async getBucketStatsStorageBucketsBucketNameStatsGet({ bucketName }: { bucketName: string }): Promise<StorageUsageStats> {
    return this.client.get<StorageUsageStats>(this.buildPath('buckets', bucketName, 'stats'));
  }
}
