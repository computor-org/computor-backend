/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Examples

 */



/**
 * Create a new example repository.
 */
export interface ExampleRepositoryCreate {
  /** Human-readable name of the repository */
  name: string;
  /** Description of the repository */
  description?: string | null;
  /** Type of source: git, minio, github, s3, gitlab */
  source_type?: string;
  /** Repository URL (Git URL, MinIO path, etc.) */
  source_url: string;
  /** Encrypted credentials */
  access_credentials?: string | null;
  /** Default version to sync from */
  default_version?: string | null;
  organization_id?: string | null;
}

/**
 * Get example repository details.
 */
export interface ExampleRepositoryGet {
  /** Human-readable name of the repository */
  name: string;
  /** Description of the repository */
  description?: string | null;
  /** Type of source: git, minio, github, s3, gitlab */
  source_type?: string;
  /** Repository URL (Git URL, MinIO path, etc.) */
  source_url: string;
  /** Encrypted credentials */
  access_credentials?: string | null;
  /** Default version to sync from */
  default_version?: string | null;
  organization_id?: string | null;
  created_at: string;
  updated_at: string;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
}

/**
 * List view of example repositories.
 */
export interface ExampleRepositoryList {
  id: string;
  name: string;
  description?: string | null;
  source_type: string;
  source_url: string;
  organization_id?: string | null;
}

/**
 * Update example repository.
 */
export interface ExampleRepositoryUpdate {
  name?: string | null;
  description?: string | null;
  access_credentials?: string | null;
  default_version?: string | null;
}

/**
 * Create a new example.
 */
export interface ExampleCreate {
  example_repository_id: string;
  directory: string;
  /** Hierarchical identifier with dots as separators */
  identifier: string;
  title: string;
  description?: string | null;
  subject?: string | null;
  category?: string | null;
  tags?: string[];
}

/**
 * Get example details.
 */
export interface ExampleGet {
  example_repository_id: string;
  directory: string;
  /** Hierarchical identifier with dots as separators */
  identifier: string;
  title: string;
  description?: string | null;
  subject?: string | null;
  category?: string | null;
  tags?: string[];
  created_at: string;
  updated_at: string;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  repository?: ExampleRepositoryGet | null;
  versions?: ExampleVersionGet[] | null;
  dependencies?: ExampleDependencyGet[] | null;
}

/**
 * List view of examples.
 */
export interface ExampleList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  id: string;
  directory: string;
  identifier: string;
  title: string;
  subject?: string | null;
  category?: string | null;
  tags?: string[];
  example_repository_id: string;
}

/**
 * Update example.
 */
export interface ExampleUpdate {
  identifier?: string | null;
  title?: string | null;
  description?: string | null;
  subject?: string | null;
  category?: string | null;
  tags?: string[] | null;
}

/**
 * Create a new example version.
 */
export interface ExampleVersionCreate {
  example_id: string;
  version_tag: string;
  version_number: number;
  storage_path: string;
  /** Content of meta.yaml */
  meta_yaml: string;
  /** Content of test.yaml */
  test_yaml?: string | null;
}

/**
 * Get example version details.
 */
export interface ExampleVersionGet {
  created_at: string;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  example_id: string;
  version_tag: string;
  version_number: number;
  storage_path: string;
  meta_yaml: string;
  test_yaml?: string | null;
}

/**
 * List view of example versions.
 */
export interface ExampleVersionList {
  id: string;
  version_tag: string;
  version_number: number;
  created_at: string;
}

/**
 * Query parameters for listing example versions (filtering).
 */
export interface ExampleVersionQuery {
  skip?: number | null;
  limit?: number | null;
  version_tag?: string | null;
}

/**
 * Create example dependency.
 */
export interface ExampleDependencyCreate {
  example_id: string;
  depends_id: string;
  /** Version constraint (e.g., '>=1.2.0', '^2.1.0'). NULL means latest version. */
  version_constraint?: string | null;
}

/**
 * Get example dependency details.
 */
export interface ExampleDependencyGet {
  id: string;
  example_id: string;
  depends_id: string;
  /** Version constraint string */
  version_constraint?: string | null;
  created_at: string;
  dependency?: ExampleList | null;
}

/**
 * Query parameters for listing examples.
 */
export interface ExampleQuery {
  skip?: number | null;
  limit?: number | null;
  repository_id?: string | null;
  /** Filter by identifier (supports Ltree patterns with *) */
  identifier?: string | null;
  title?: string | null;
  category?: string | null;
  tags?: string[] | null;
  search?: string | null;
}

/**
 * Query parameters for listing repositories.
 */
export interface ExampleRepositoryQuery {
  skip?: number | null;
  limit?: number | null;
  name?: string | null;
  source_type?: string | null;
  organization_id?: string | null;
}

/**
 * Request to upload an example to storage.
 */
export interface ExampleUploadRequest {
  repository_id: string;
  directory: string;
  /** Map of filename to content. Text files as UTF-8 strings, binary files as either base64-encoded strings or raw bytes. Must include meta.yaml */
  files: Record<string, string | any>;
}

/**
 * Request to upload multiple examples to storage.
 */
export interface ExampleBatchUploadRequest {
  repository_id: string;
  /** List of examples with directory and files */
  examples: Record<string, any>[];
}

/**
 * Files for a single example.
 */
export interface ExampleFileSet {
  example_id: string;
  version_id: string;
  version_tag: string;
  directory: string;
  identifier: string;
  title: string;
  /** Map of filename to content */
  files: Record<string, string>;
  meta_yaml: string;
  test_yaml?: string | null;
}

/**
 * Response containing downloaded example files.
 */
export interface ExampleDownloadResponse {
  example_id: string;
  version_id?: string | null;
  version_tag: string;
  /** Map of filename to content */
  files: Record<string, string>;
  meta_yaml: string;
  test_yaml?: string | null;
  /** Dependency examples when with_dependencies=True */
  dependencies?: ExampleFileSet[] | null;
}

/**
 * Request to assign multiple examples to course contents.
 */
export interface BulkAssignExamplesRequest {
  /** List of assignments with course_content_id, example_id, and example_version */
  assignments: Record<string, string>[];
}