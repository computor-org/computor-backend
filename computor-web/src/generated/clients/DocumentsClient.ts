/**
 * Auto-generated client for DocumentsClient.
 * Endpoint: /documents
 */

import type { DocumentDelete, DocumentDirectoryCreate, DocumentDirectoryDelete, DocumentDirectoryGet, DocumentDirectoryRename, DocumentGet, DocumentList, DocumentRename } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class DocumentsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/documents');
  }

  /**
   * Delete Document Directory
   * Delete a documents directory recursively.
   * Refuses (409) when the leading segment matches an entity's path —
   * those directories are entity-bound and can only be removed via
   * entity deletion.
   */
  async deleteDocumentDirectoryDocumentsDirectoriesDelete({ userId, body }: { userId?: string | null; body: DocumentDirectoryDelete }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath('directories'), { data: body, params: queryParams });
  }

  /**
   * Rename Document Directory
   * Rename a documents directory inside the same scope.
   * Source must exist and be a directory; target must not exist;
   * target must not lie inside the source (no moving a dir into
   * itself). ``created`` in the response is always ``False`` — the
   * directory was moved, not freshly created.
   */
  async renameDocumentDirectoryDocumentsDirectoriesPatch({ userId, body }: { userId?: string | null; body: DocumentDirectoryRename }): Promise<DocumentDirectoryGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<DocumentDirectoryGet>(this.buildPath('directories'), body, { params: queryParams });
  }

  /**
   * Create Document Directory
   * Create a documents directory (idempotent — returns ``created=False``
   * when it already existed).
   */
  async createDocumentDirectoryDocumentsDirectoriesPost({ userId, body }: { userId?: string | null; body: DocumentDirectoryCreate }): Promise<DocumentDirectoryGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<DocumentDirectoryGet>(this.buildPath('directories'), body, { params: queryParams });
  }

  /**
   * Delete Document File
   * Delete a documents file.
   */
  async deleteDocumentFileDocumentsFilesDelete({ userId, body }: { userId?: string | null; body: DocumentDelete }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath('files'), { data: body, params: queryParams });
  }

  /**
   * Get Document File
   * Fetch a documents file. Available to any authenticated user.
   * The same content is reachable unauthenticated via the static-server
   * at ``/docs/<...>``; this endpoint serves authenticated callers
   * through the same auth chain they use for everything else.
   * Supports ``If-None-Match`` for cheap revalidation: when the
   * supplied ETag matches the current file, returns ``304 Not
   * Modified`` with the same ``ETag`` and ``Last-Modified`` headers
   * the 200 response would carry.
   */
  async getDocumentFileDocumentsFilesGet({ path, scope, scopeId, userId }: { path: string; scope: 'system' | 'organization' | 'course_family' | 'course'; scopeId?: string | null; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      path,
      scope,
      scope_id: scopeId,
      user_id: userId,
    };
    return this.client.get<void>(this.buildPath('files'), { params: queryParams });
  }

  /**
   * Rename Document File
   * Rename a documents file inside the same scope.
   * Source must exist and be a file; target must not exist. Both
   * paths are validated. Atomic on the same filesystem (which is
   * always true for ``DOCUMENTS_ROOT``).
   */
  async renameDocumentFileDocumentsFilesPatch({ userId, body }: { userId?: string | null; body: DocumentRename }): Promise<DocumentGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<DocumentGet>(this.buildPath('files'), body, { params: queryParams });
  }

  /**
   * Upload Document File
   * Create or overwrite a documents file at the given scope and path.
   */
  async uploadDocumentFileDocumentsFilesPost({ userId }: { userId?: string | null }): Promise<DocumentGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<DocumentGet>(this.buildPath('files'), { params: queryParams });
  }

  /**
   * List Documents Directory
   * List entries in a documents directory.
   * Available to any authenticated user. An unwritten scope root
   * returns an empty list (so a fresh course/family/org does not 404);
   * a missing non-root path is a 404.
   */
  async listDocumentsDirectoryDocumentsListGet({ path, scope, scopeId, userId }: { path?: string | null; scope: 'system' | 'organization' | 'course_family' | 'course'; scopeId?: string | null; userId?: string | null }): Promise<DocumentList[]> {
    const queryParams: Record<string, unknown> = {
      path,
      scope,
      scope_id: scopeId,
      user_id: userId,
    };
    return this.client.get<DocumentList[]>(this.buildPath('list'), { params: queryParams });
  }
}
