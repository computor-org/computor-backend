/**
 * Auto-generated client for StorageClient.
 * Endpoint: /storage
 */

import type { BucketCreate, BucketInfo, PresignedUrlRequest, PresignedUrlResponse, StorageObjectGet, StorageObjectList, StorageUsageStats } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class StorageClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/storage');
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

  /**
   * Copy Object
   * Copy an object within or between buckets
   */
  async copyObjectStorageCopyPost(): Promise<void> {
    return this.client.post<void>(this.buildPath('copy'));
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
  async listObjectsStorageObjectsGet({ bucketName, contentType, limit, maxSize, minSize, prefix, skip }: { bucketName?: string | null; contentType?: string | null; limit?: number | null; maxSize?: number | null; minSize?: number | null; prefix?: string | null; skip?: number | null }): Promise<StorageObjectList[]> {
    const queryParams: Record<string, unknown> = {
      bucket_name: bucketName,
      content_type: contentType,
      limit,
      max_size: maxSize,
      min_size: minSize,
      prefix,
      skip,
    };
    return this.client.get<StorageObjectList[]>(this.buildPath('objects'), { params: queryParams });
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
   * Generate Presigned Url
   * Generate a presigned URL for direct object access
   */
  async generatePresignedUrlStoragePresignedUrlPost({ body }: { body: PresignedUrlRequest }): Promise<PresignedUrlResponse> {
    return this.client.post<PresignedUrlResponse>(this.buildPath('presigned-url'), body);
  }

  /**
   * Upload File
   * Upload a file to storage with security validation
   */
  async uploadFileStorageUploadPost({ userId }: { userId?: string | null }): Promise<StorageObjectGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<StorageObjectGet>(this.buildPath('upload'), { params: queryParams });
  }
}
