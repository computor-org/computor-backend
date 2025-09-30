/**
 * Auto-generated validation classes for Examples models
 * DO NOT EDIT MANUALLY
 */

import type { AssignExampleRequest, BulkAssignExamplesRequest, DeployExampleRequest, ExampleBatchUploadRequest, ExampleCreate, ExampleDependencyCreate, ExampleDependencyGet, ExampleDownloadResponse, ExampleFileSet, ExampleGet, ExampleList, ExampleQuery, ExampleRepositoryCreate, ExampleRepositoryGet, ExampleRepositoryList, ExampleRepositoryQuery, ExampleRepositoryUpdate, ExampleUpdate, ExampleUploadRequest, ExampleVersionCreate, ExampleVersionGet, ExampleVersionList, ExampleVersionQuery, ExamplesUploadConfig } from '../generated/examples';
import { BaseValidator, ValidationError } from './BaseValidator';

/**
 * Request to assign an example to course content.
 */
export class AssignExampleRequestValidator extends BaseValidator<AssignExampleRequest> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Request to assign an example to course content.",
  "properties": {
    "example_version_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Example version to assign (optional if providing identifier+version_tag)",
      "title": "Example Version Id"
    },
    "example_identifier": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Hierarchical identifier (ltree string) for the example source",
      "title": "Example Identifier"
    },
    "version_tag": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Version tag for the example source",
      "title": "Version Tag"
    },
    "deployment_message": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Optional message about this assignment",
      "title": "Deployment Message"
    }
  },
  "title": "AssignExampleRequest",
  "type": "object",
  "x-model-name": "AssignExampleRequest"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): AssignExampleRequest {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('AssignExampleRequest', 'Expected an object');
    }

    // Optional field: example_version_id
    if ('example_version_id' in data && data.example_version_id !== undefined && data.example_version_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: example_identifier
    if ('example_identifier' in data && data.example_identifier !== undefined && data.example_identifier !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: version_tag
    if ('version_tag' in data && data.version_tag !== undefined && data.version_tag !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: deployment_message
    if ('deployment_message' in data && data.deployment_message !== undefined && data.deployment_message !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('AssignExampleRequest', errors.join('; '));
    }

    return data as AssignExampleRequest;
  }

  safeValidate(data: any): { success: true; data: AssignExampleRequest } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('AssignExampleRequest', String(error)) };
    }
  }
}

/**
 * Request to deploy assigned examples.
 */
export class DeployExampleRequestValidator extends BaseValidator<DeployExampleRequest> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Request to deploy assigned examples.",
  "properties": {
    "course_id": {
      "description": "Course to deploy examples for",
      "title": "Course Id",
      "type": "string"
    },
    "content_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Specific content IDs to deploy (all if None)",
      "title": "Content Ids"
    },
    "force": {
      "default": false,
      "description": "Force re-deployment even if already deployed",
      "title": "Force",
      "type": "boolean"
    }
  },
  "required": [
    "course_id"
  ],
  "title": "DeployExampleRequest",
  "type": "object",
  "x-model-name": "DeployExampleRequest"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): DeployExampleRequest {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('DeployExampleRequest', 'Expected an object');
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Optional field: content_ids
    if ('content_ids' in data && data.content_ids !== undefined && data.content_ids !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: force
    if ('force' in data && data.force !== undefined && data.force !== null) {
      if (typeof data.force !== 'boolean') {
        errors.push('Field force must be a boolean');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('DeployExampleRequest', errors.join('; '));
    }

    return data as DeployExampleRequest;
  }

  safeValidate(data: any): { success: true; data: DeployExampleRequest } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('DeployExampleRequest', String(error)) };
    }
  }
}

/**
 * Request to assign multiple examples to course contents.
 */
export class BulkAssignExamplesRequestValidator extends BaseValidator<BulkAssignExamplesRequest> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Request to assign multiple examples to course contents.",
  "properties": {
    "assignments": {
      "description": "List of assignments with course_content_id, example_id, and example_version",
      "items": {
        "additionalProperties": {
          "type": "string"
        },
        "type": "object"
      },
      "title": "Assignments",
      "type": "array"
    }
  },
  "required": [
    "assignments"
  ],
  "title": "BulkAssignExamplesRequest",
  "type": "object",
  "x-model-name": "BulkAssignExamplesRequest"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): BulkAssignExamplesRequest {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('BulkAssignExamplesRequest', 'Expected an object');
    }

    // Required field: assignments
    if (!('assignments' in data)) {
      errors.push('Missing required field: assignments');
    } else {
      if (!Array.isArray(data.assignments)) {
        errors.push('Field assignments must be an array');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('BulkAssignExamplesRequest', errors.join('; '));
    }

    return data as BulkAssignExamplesRequest;
  }

  safeValidate(data: any): { success: true; data: BulkAssignExamplesRequest } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('BulkAssignExamplesRequest', String(error)) };
    }
  }
}

/**
 * Create a new example repository.
 */
export class ExampleRepositoryCreateValidator extends BaseValidator<ExampleRepositoryCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Create a new example repository.",
  "properties": {
    "name": {
      "description": "Human-readable name of the repository",
      "title": "Name",
      "type": "string"
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Description of the repository",
      "title": "Description"
    },
    "source_type": {
      "default": "git",
      "description": "Type of source: git, minio, github, s3, gitlab",
      "title": "Source Type",
      "type": "string"
    },
    "source_url": {
      "description": "Repository URL (Git URL, MinIO path, etc.)",
      "title": "Source Url",
      "type": "string"
    },
    "access_credentials": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Encrypted credentials",
      "title": "Access Credentials"
    },
    "default_version": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Default version to sync from",
      "title": "Default Version"
    },
    "organization_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Organization Id"
    }
  },
  "required": [
    "name",
    "source_url"
  ],
  "title": "ExampleRepositoryCreate",
  "type": "object",
  "x-model-name": "ExampleRepositoryCreate"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleRepositoryCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleRepositoryCreate', 'Expected an object');
    }

    // Required field: name
    if (!('name' in data)) {
      errors.push('Missing required field: name');
    } else {
      if (typeof data.name !== 'string') {
        errors.push('Field name must be a string');
      }
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: source_type
    if ('source_type' in data && data.source_type !== undefined && data.source_type !== null) {
      if (typeof data.source_type !== 'string') {
        errors.push('Field source_type must be a string');
      }
    }

    // Required field: source_url
    if (!('source_url' in data)) {
      errors.push('Missing required field: source_url');
    } else {
      if (typeof data.source_url !== 'string') {
        errors.push('Field source_url must be a string');
      }
    }

    // Optional field: access_credentials
    if ('access_credentials' in data && data.access_credentials !== undefined && data.access_credentials !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: default_version
    if ('default_version' in data && data.default_version !== undefined && data.default_version !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: organization_id
    if ('organization_id' in data && data.organization_id !== undefined && data.organization_id !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleRepositoryCreate', errors.join('; '));
    }

    return data as ExampleRepositoryCreate;
  }

  safeValidate(data: any): { success: true; data: ExampleRepositoryCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleRepositoryCreate', String(error)) };
    }
  }
}

/**
 * Get example repository details.
 */
export class ExampleRepositoryGetValidator extends BaseValidator<ExampleRepositoryGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Get example repository details.",
  "properties": {
    "name": {
      "description": "Human-readable name of the repository",
      "title": "Name",
      "type": "string"
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Description of the repository",
      "title": "Description"
    },
    "source_type": {
      "default": "git",
      "description": "Type of source: git, minio, github, s3, gitlab",
      "title": "Source Type",
      "type": "string"
    },
    "source_url": {
      "description": "Repository URL (Git URL, MinIO path, etc.)",
      "title": "Source Url",
      "type": "string"
    },
    "access_credentials": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Encrypted credentials",
      "title": "Access Credentials"
    },
    "default_version": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Default version to sync from",
      "title": "Default Version"
    },
    "organization_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Organization Id"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "updated_at": {
      "format": "date-time",
      "title": "Updated At",
      "type": "string"
    },
    "created_by": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Created By"
    },
    "updated_by": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Updated By"
    },
    "id": {
      "title": "Id",
      "type": "string"
    }
  },
  "required": [
    "name",
    "source_url",
    "created_at",
    "updated_at",
    "id"
  ],
  "title": "ExampleRepositoryGet",
  "type": "object",
  "x-model-name": "ExampleRepositoryGet"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleRepositoryGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleRepositoryGet', 'Expected an object');
    }

    // Required field: name
    if (!('name' in data)) {
      errors.push('Missing required field: name');
    } else {
      if (typeof data.name !== 'string') {
        errors.push('Field name must be a string');
      }
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: source_type
    if ('source_type' in data && data.source_type !== undefined && data.source_type !== null) {
      if (typeof data.source_type !== 'string') {
        errors.push('Field source_type must be a string');
      }
    }

    // Required field: source_url
    if (!('source_url' in data)) {
      errors.push('Missing required field: source_url');
    } else {
      if (typeof data.source_url !== 'string') {
        errors.push('Field source_url must be a string');
      }
    }

    // Optional field: access_credentials
    if ('access_credentials' in data && data.access_credentials !== undefined && data.access_credentials !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: default_version
    if ('default_version' in data && data.default_version !== undefined && data.default_version !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: organization_id
    if ('organization_id' in data && data.organization_id !== undefined && data.organization_id !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: created_at
    if (!('created_at' in data)) {
      errors.push('Missing required field: created_at');
    } else {
      if (typeof data.created_at !== 'string') {
        errors.push('Field created_at must be a string');
      }
    }

    // Required field: updated_at
    if (!('updated_at' in data)) {
      errors.push('Missing required field: updated_at');
    } else {
      if (typeof data.updated_at !== 'string') {
        errors.push('Field updated_at must be a string');
      }
    }

    // Optional field: created_by
    if ('created_by' in data && data.created_by !== undefined && data.created_by !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: updated_by
    if ('updated_by' in data && data.updated_by !== undefined && data.updated_by !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: id
    if (!('id' in data)) {
      errors.push('Missing required field: id');
    } else {
      if (typeof data.id !== 'string') {
        errors.push('Field id must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleRepositoryGet', errors.join('; '));
    }

    return data as ExampleRepositoryGet;
  }

  safeValidate(data: any): { success: true; data: ExampleRepositoryGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleRepositoryGet', String(error)) };
    }
  }
}

/**
 * List view of example repositories.
 */
export class ExampleRepositoryListValidator extends BaseValidator<ExampleRepositoryList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "List view of example repositories.",
  "properties": {
    "id": {
      "title": "Id",
      "type": "string"
    },
    "name": {
      "title": "Name",
      "type": "string"
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "source_type": {
      "title": "Source Type",
      "type": "string"
    },
    "source_url": {
      "title": "Source Url",
      "type": "string"
    },
    "organization_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Organization Id"
    }
  },
  "required": [
    "id",
    "name",
    "source_type",
    "source_url"
  ],
  "title": "ExampleRepositoryList",
  "type": "object",
  "x-model-name": "ExampleRepositoryList"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleRepositoryList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleRepositoryList', 'Expected an object');
    }

    // Required field: id
    if (!('id' in data)) {
      errors.push('Missing required field: id');
    } else {
      if (typeof data.id !== 'string') {
        errors.push('Field id must be a string');
      }
    }

    // Required field: name
    if (!('name' in data)) {
      errors.push('Missing required field: name');
    } else {
      if (typeof data.name !== 'string') {
        errors.push('Field name must be a string');
      }
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: source_type
    if (!('source_type' in data)) {
      errors.push('Missing required field: source_type');
    } else {
      if (typeof data.source_type !== 'string') {
        errors.push('Field source_type must be a string');
      }
    }

    // Required field: source_url
    if (!('source_url' in data)) {
      errors.push('Missing required field: source_url');
    } else {
      if (typeof data.source_url !== 'string') {
        errors.push('Field source_url must be a string');
      }
    }

    // Optional field: organization_id
    if ('organization_id' in data && data.organization_id !== undefined && data.organization_id !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleRepositoryList', errors.join('; '));
    }

    return data as ExampleRepositoryList;
  }

  safeValidate(data: any): { success: true; data: ExampleRepositoryList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleRepositoryList', String(error)) };
    }
  }
}

/**
 * Update example repository.
 */
export class ExampleRepositoryUpdateValidator extends BaseValidator<ExampleRepositoryUpdate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Update example repository.",
  "properties": {
    "name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Name"
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "access_credentials": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Access Credentials"
    },
    "default_version": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Default Version"
    }
  },
  "title": "ExampleRepositoryUpdate",
  "type": "object",
  "x-model-name": "ExampleRepositoryUpdate"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleRepositoryUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleRepositoryUpdate', 'Expected an object');
    }

    // Optional field: name
    if ('name' in data && data.name !== undefined && data.name !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: access_credentials
    if ('access_credentials' in data && data.access_credentials !== undefined && data.access_credentials !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: default_version
    if ('default_version' in data && data.default_version !== undefined && data.default_version !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleRepositoryUpdate', errors.join('; '));
    }

    return data as ExampleRepositoryUpdate;
  }

  safeValidate(data: any): { success: true; data: ExampleRepositoryUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleRepositoryUpdate', String(error)) };
    }
  }
}

/**
 * Create a new example.
 */
export class ExampleCreateValidator extends BaseValidator<ExampleCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Create a new example.",
  "properties": {
    "example_repository_id": {
      "title": "Example Repository Id",
      "type": "string"
    },
    "directory": {
      "pattern": "^[a-zA-Z0-9._-]+$",
      "title": "Directory",
      "type": "string"
    },
    "identifier": {
      "description": "Hierarchical identifier with dots as separators",
      "title": "Identifier",
      "type": "string"
    },
    "title": {
      "title": "Title",
      "type": "string"
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "subject": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Subject"
    },
    "category": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Category"
    },
    "tags": {
      "items": {
        "type": "string"
      },
      "title": "Tags",
      "type": "array"
    }
  },
  "required": [
    "example_repository_id",
    "directory",
    "identifier",
    "title"
  ],
  "title": "ExampleCreate",
  "type": "object",
  "x-model-name": "ExampleCreate"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleCreate', 'Expected an object');
    }

    // Required field: example_repository_id
    if (!('example_repository_id' in data)) {
      errors.push('Missing required field: example_repository_id');
    } else {
      if (typeof data.example_repository_id !== 'string') {
        errors.push('Field example_repository_id must be a string');
      }
    }

    // Required field: directory
    if (!('directory' in data)) {
      errors.push('Missing required field: directory');
    } else {
      if (typeof data.directory !== 'string') {
        errors.push('Field directory must be a string');
      }
    }

    // Required field: identifier
    if (!('identifier' in data)) {
      errors.push('Missing required field: identifier');
    } else {
      if (typeof data.identifier !== 'string') {
        errors.push('Field identifier must be a string');
      }
    }

    // Required field: title
    if (!('title' in data)) {
      errors.push('Missing required field: title');
    } else {
      if (typeof data.title !== 'string') {
        errors.push('Field title must be a string');
      }
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: subject
    if ('subject' in data && data.subject !== undefined && data.subject !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: category
    if ('category' in data && data.category !== undefined && data.category !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: tags
    if ('tags' in data && data.tags !== undefined && data.tags !== null) {
      if (!Array.isArray(data.tags)) {
        errors.push('Field tags must be an array');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleCreate', errors.join('; '));
    }

    return data as ExampleCreate;
  }

  safeValidate(data: any): { success: true; data: ExampleCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleCreate', String(error)) };
    }
  }
}

/**
 * Get example details.
 */
export class ExampleGetValidator extends BaseValidator<ExampleGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "ExampleDependencyGet": {
      "description": "Get example dependency details.",
      "properties": {
        "id": {
          "title": "Id",
          "type": "string"
        },
        "example_id": {
          "title": "Example Id",
          "type": "string"
        },
        "depends_id": {
          "title": "Depends Id",
          "type": "string"
        },
        "version_constraint": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Version constraint string",
          "title": "Version Constraint"
        },
        "created_at": {
          "format": "date-time",
          "title": "Created At",
          "type": "string"
        },
        "dependency": {
          "anyOf": [
            {
              "$ref": "#/$defs/ExampleList"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "required": [
        "id",
        "example_id",
        "depends_id",
        "created_at"
      ],
      "title": "ExampleDependencyGet",
      "type": "object"
    },
    "ExampleList": {
      "description": "List view of examples.",
      "properties": {
        "created_at": {
          "anyOf": [
            {
              "format": "date-time",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Creation timestamp",
          "title": "Created At"
        },
        "updated_at": {
          "anyOf": [
            {
              "format": "date-time",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Update timestamp",
          "title": "Updated At"
        },
        "id": {
          "title": "Id",
          "type": "string"
        },
        "directory": {
          "title": "Directory",
          "type": "string"
        },
        "identifier": {
          "title": "Identifier",
          "type": "string"
        },
        "title": {
          "title": "Title",
          "type": "string"
        },
        "subject": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Subject"
        },
        "category": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Category"
        },
        "tags": {
          "default": [],
          "items": {
            "type": "string"
          },
          "title": "Tags",
          "type": "array"
        },
        "example_repository_id": {
          "title": "Example Repository Id",
          "type": "string"
        }
      },
      "required": [
        "id",
        "directory",
        "identifier",
        "title",
        "example_repository_id"
      ],
      "title": "ExampleList",
      "type": "object"
    },
    "ExampleRepositoryGet": {
      "description": "Get example repository details.",
      "properties": {
        "name": {
          "description": "Human-readable name of the repository",
          "title": "Name",
          "type": "string"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Description of the repository",
          "title": "Description"
        },
        "source_type": {
          "default": "git",
          "description": "Type of source: git, minio, github, s3, gitlab",
          "title": "Source Type",
          "type": "string"
        },
        "source_url": {
          "description": "Repository URL (Git URL, MinIO path, etc.)",
          "title": "Source Url",
          "type": "string"
        },
        "access_credentials": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Encrypted credentials",
          "title": "Access Credentials"
        },
        "default_version": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Default version to sync from",
          "title": "Default Version"
        },
        "organization_id": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Organization Id"
        },
        "created_at": {
          "format": "date-time",
          "title": "Created At",
          "type": "string"
        },
        "updated_at": {
          "format": "date-time",
          "title": "Updated At",
          "type": "string"
        },
        "created_by": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Created By"
        },
        "updated_by": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Updated By"
        },
        "id": {
          "title": "Id",
          "type": "string"
        }
      },
      "required": [
        "name",
        "source_url",
        "created_at",
        "updated_at",
        "id"
      ],
      "title": "ExampleRepositoryGet",
      "type": "object"
    },
    "ExampleVersionGet": {
      "description": "Get example version details.",
      "properties": {
        "created_at": {
          "format": "date-time",
          "title": "Created At",
          "type": "string"
        },
        "updated_at": {
          "anyOf": [
            {
              "format": "date-time",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Update timestamp",
          "title": "Updated At"
        },
        "created_by": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Created By"
        },
        "updated_by": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Updated By"
        },
        "id": {
          "title": "Id",
          "type": "string"
        },
        "example_id": {
          "title": "Example Id",
          "type": "string"
        },
        "version_tag": {
          "title": "Version Tag",
          "type": "string"
        },
        "version_number": {
          "title": "Version Number",
          "type": "integer"
        },
        "storage_path": {
          "title": "Storage Path",
          "type": "string"
        },
        "meta_yaml": {
          "title": "Meta Yaml",
          "type": "string"
        },
        "test_yaml": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Test Yaml"
        }
      },
      "required": [
        "created_at",
        "id",
        "example_id",
        "version_tag",
        "version_number",
        "storage_path",
        "meta_yaml"
      ],
      "title": "ExampleVersionGet",
      "type": "object"
    }
  },
  "description": "Get example details.",
  "properties": {
    "example_repository_id": {
      "title": "Example Repository Id",
      "type": "string"
    },
    "directory": {
      "pattern": "^[a-zA-Z0-9._-]+$",
      "title": "Directory",
      "type": "string"
    },
    "identifier": {
      "description": "Hierarchical identifier with dots as separators",
      "title": "Identifier",
      "type": "string"
    },
    "title": {
      "title": "Title",
      "type": "string"
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "subject": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Subject"
    },
    "category": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Category"
    },
    "tags": {
      "items": {
        "type": "string"
      },
      "title": "Tags",
      "type": "array"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "updated_at": {
      "format": "date-time",
      "title": "Updated At",
      "type": "string"
    },
    "created_by": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Created By"
    },
    "updated_by": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Updated By"
    },
    "id": {
      "title": "Id",
      "type": "string"
    },
    "repository": {
      "anyOf": [
        {
          "$ref": "#/$defs/ExampleRepositoryGet"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "versions": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/ExampleVersionGet"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Versions"
    },
    "dependencies": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/ExampleDependencyGet"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Dependencies"
    }
  },
  "required": [
    "example_repository_id",
    "directory",
    "identifier",
    "title",
    "created_at",
    "updated_at",
    "id"
  ],
  "title": "ExampleGet",
  "type": "object",
  "x-model-name": "ExampleGet"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleGet', 'Expected an object');
    }

    // Required field: example_repository_id
    if (!('example_repository_id' in data)) {
      errors.push('Missing required field: example_repository_id');
    } else {
      if (typeof data.example_repository_id !== 'string') {
        errors.push('Field example_repository_id must be a string');
      }
    }

    // Required field: directory
    if (!('directory' in data)) {
      errors.push('Missing required field: directory');
    } else {
      if (typeof data.directory !== 'string') {
        errors.push('Field directory must be a string');
      }
    }

    // Required field: identifier
    if (!('identifier' in data)) {
      errors.push('Missing required field: identifier');
    } else {
      if (typeof data.identifier !== 'string') {
        errors.push('Field identifier must be a string');
      }
    }

    // Required field: title
    if (!('title' in data)) {
      errors.push('Missing required field: title');
    } else {
      if (typeof data.title !== 'string') {
        errors.push('Field title must be a string');
      }
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: subject
    if ('subject' in data && data.subject !== undefined && data.subject !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: category
    if ('category' in data && data.category !== undefined && data.category !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: tags
    if ('tags' in data && data.tags !== undefined && data.tags !== null) {
      if (!Array.isArray(data.tags)) {
        errors.push('Field tags must be an array');
      }
    }

    // Required field: created_at
    if (!('created_at' in data)) {
      errors.push('Missing required field: created_at');
    } else {
      if (typeof data.created_at !== 'string') {
        errors.push('Field created_at must be a string');
      }
    }

    // Required field: updated_at
    if (!('updated_at' in data)) {
      errors.push('Missing required field: updated_at');
    } else {
      if (typeof data.updated_at !== 'string') {
        errors.push('Field updated_at must be a string');
      }
    }

    // Optional field: created_by
    if ('created_by' in data && data.created_by !== undefined && data.created_by !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: updated_by
    if ('updated_by' in data && data.updated_by !== undefined && data.updated_by !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: id
    if (!('id' in data)) {
      errors.push('Missing required field: id');
    } else {
      if (typeof data.id !== 'string') {
        errors.push('Field id must be a string');
      }
    }

    // Optional field: repository
    if ('repository' in data && data.repository !== undefined && data.repository !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: versions
    if ('versions' in data && data.versions !== undefined && data.versions !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: dependencies
    if ('dependencies' in data && data.dependencies !== undefined && data.dependencies !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleGet', errors.join('; '));
    }

    return data as ExampleGet;
  }

  safeValidate(data: any): { success: true; data: ExampleGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleGet', String(error)) };
    }
  }
}

/**
 * List view of examples.
 */
export class ExampleListValidator extends BaseValidator<ExampleList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "List view of examples.",
  "properties": {
    "created_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Creation timestamp",
      "title": "Created At"
    },
    "updated_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Update timestamp",
      "title": "Updated At"
    },
    "id": {
      "title": "Id",
      "type": "string"
    },
    "directory": {
      "title": "Directory",
      "type": "string"
    },
    "identifier": {
      "title": "Identifier",
      "type": "string"
    },
    "title": {
      "title": "Title",
      "type": "string"
    },
    "subject": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Subject"
    },
    "category": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Category"
    },
    "tags": {
      "default": [],
      "items": {
        "type": "string"
      },
      "title": "Tags",
      "type": "array"
    },
    "example_repository_id": {
      "title": "Example Repository Id",
      "type": "string"
    }
  },
  "required": [
    "id",
    "directory",
    "identifier",
    "title",
    "example_repository_id"
  ],
  "title": "ExampleList",
  "type": "object",
  "x-model-name": "ExampleList"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleList', 'Expected an object');
    }

    // Optional field: created_at
    if ('created_at' in data && data.created_at !== undefined && data.created_at !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: updated_at
    if ('updated_at' in data && data.updated_at !== undefined && data.updated_at !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: id
    if (!('id' in data)) {
      errors.push('Missing required field: id');
    } else {
      if (typeof data.id !== 'string') {
        errors.push('Field id must be a string');
      }
    }

    // Required field: directory
    if (!('directory' in data)) {
      errors.push('Missing required field: directory');
    } else {
      if (typeof data.directory !== 'string') {
        errors.push('Field directory must be a string');
      }
    }

    // Required field: identifier
    if (!('identifier' in data)) {
      errors.push('Missing required field: identifier');
    } else {
      if (typeof data.identifier !== 'string') {
        errors.push('Field identifier must be a string');
      }
    }

    // Required field: title
    if (!('title' in data)) {
      errors.push('Missing required field: title');
    } else {
      if (typeof data.title !== 'string') {
        errors.push('Field title must be a string');
      }
    }

    // Optional field: subject
    if ('subject' in data && data.subject !== undefined && data.subject !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: category
    if ('category' in data && data.category !== undefined && data.category !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: tags
    if ('tags' in data && data.tags !== undefined && data.tags !== null) {
      if (!Array.isArray(data.tags)) {
        errors.push('Field tags must be an array');
      }
    }

    // Required field: example_repository_id
    if (!('example_repository_id' in data)) {
      errors.push('Missing required field: example_repository_id');
    } else {
      if (typeof data.example_repository_id !== 'string') {
        errors.push('Field example_repository_id must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleList', errors.join('; '));
    }

    return data as ExampleList;
  }

  safeValidate(data: any): { success: true; data: ExampleList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleList', String(error)) };
    }
  }
}

/**
 * Update example.
 */
export class ExampleUpdateValidator extends BaseValidator<ExampleUpdate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Update example.",
  "properties": {
    "identifier": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Identifier"
    },
    "title": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Title"
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "subject": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Subject"
    },
    "category": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Category"
    },
    "tags": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Tags"
    }
  },
  "title": "ExampleUpdate",
  "type": "object",
  "x-model-name": "ExampleUpdate"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleUpdate', 'Expected an object');
    }

    // Optional field: identifier
    if ('identifier' in data && data.identifier !== undefined && data.identifier !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: subject
    if ('subject' in data && data.subject !== undefined && data.subject !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: category
    if ('category' in data && data.category !== undefined && data.category !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: tags
    if ('tags' in data && data.tags !== undefined && data.tags !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleUpdate', errors.join('; '));
    }

    return data as ExampleUpdate;
  }

  safeValidate(data: any): { success: true; data: ExampleUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleUpdate', String(error)) };
    }
  }
}

/**
 * Create a new example version.
 */
export class ExampleVersionCreateValidator extends BaseValidator<ExampleVersionCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Create a new example version.",
  "properties": {
    "example_id": {
      "title": "Example Id",
      "type": "string"
    },
    "version_tag": {
      "maxLength": 64,
      "title": "Version Tag",
      "type": "string"
    },
    "version_number": {
      "minimum": 1,
      "title": "Version Number",
      "type": "integer"
    },
    "storage_path": {
      "title": "Storage Path",
      "type": "string"
    },
    "meta_yaml": {
      "description": "Content of meta.yaml",
      "title": "Meta Yaml",
      "type": "string"
    },
    "test_yaml": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Content of test.yaml",
      "title": "Test Yaml"
    }
  },
  "required": [
    "example_id",
    "version_tag",
    "version_number",
    "storage_path",
    "meta_yaml"
  ],
  "title": "ExampleVersionCreate",
  "type": "object",
  "x-model-name": "ExampleVersionCreate"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleVersionCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleVersionCreate', 'Expected an object');
    }

    // Required field: example_id
    if (!('example_id' in data)) {
      errors.push('Missing required field: example_id');
    } else {
      if (typeof data.example_id !== 'string') {
        errors.push('Field example_id must be a string');
      }
    }

    // Required field: version_tag
    if (!('version_tag' in data)) {
      errors.push('Missing required field: version_tag');
    } else {
      if (typeof data.version_tag !== 'string') {
        errors.push('Field version_tag must be a string');
      }
    }

    // Required field: version_number
    if (!('version_number' in data)) {
      errors.push('Missing required field: version_number');
    } else {
      if (typeof data.version_number !== 'number') {
        errors.push('Field version_number must be a number');
      }
    }

    // Required field: storage_path
    if (!('storage_path' in data)) {
      errors.push('Missing required field: storage_path');
    } else {
      if (typeof data.storage_path !== 'string') {
        errors.push('Field storage_path must be a string');
      }
    }

    // Required field: meta_yaml
    if (!('meta_yaml' in data)) {
      errors.push('Missing required field: meta_yaml');
    } else {
      if (typeof data.meta_yaml !== 'string') {
        errors.push('Field meta_yaml must be a string');
      }
    }

    // Optional field: test_yaml
    if ('test_yaml' in data && data.test_yaml !== undefined && data.test_yaml !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleVersionCreate', errors.join('; '));
    }

    return data as ExampleVersionCreate;
  }

  safeValidate(data: any): { success: true; data: ExampleVersionCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleVersionCreate', String(error)) };
    }
  }
}

/**
 * Get example version details.
 */
export class ExampleVersionGetValidator extends BaseValidator<ExampleVersionGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Get example version details.",
  "properties": {
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "updated_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Update timestamp",
      "title": "Updated At"
    },
    "created_by": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Created By"
    },
    "updated_by": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Updated By"
    },
    "id": {
      "title": "Id",
      "type": "string"
    },
    "example_id": {
      "title": "Example Id",
      "type": "string"
    },
    "version_tag": {
      "title": "Version Tag",
      "type": "string"
    },
    "version_number": {
      "title": "Version Number",
      "type": "integer"
    },
    "storage_path": {
      "title": "Storage Path",
      "type": "string"
    },
    "meta_yaml": {
      "title": "Meta Yaml",
      "type": "string"
    },
    "test_yaml": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Test Yaml"
    }
  },
  "required": [
    "created_at",
    "id",
    "example_id",
    "version_tag",
    "version_number",
    "storage_path",
    "meta_yaml"
  ],
  "title": "ExampleVersionGet",
  "type": "object",
  "x-model-name": "ExampleVersionGet"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleVersionGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleVersionGet', 'Expected an object');
    }

    // Required field: created_at
    if (!('created_at' in data)) {
      errors.push('Missing required field: created_at');
    } else {
      if (typeof data.created_at !== 'string') {
        errors.push('Field created_at must be a string');
      }
    }

    // Optional field: updated_at
    if ('updated_at' in data && data.updated_at !== undefined && data.updated_at !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: created_by
    if ('created_by' in data && data.created_by !== undefined && data.created_by !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: updated_by
    if ('updated_by' in data && data.updated_by !== undefined && data.updated_by !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: id
    if (!('id' in data)) {
      errors.push('Missing required field: id');
    } else {
      if (typeof data.id !== 'string') {
        errors.push('Field id must be a string');
      }
    }

    // Required field: example_id
    if (!('example_id' in data)) {
      errors.push('Missing required field: example_id');
    } else {
      if (typeof data.example_id !== 'string') {
        errors.push('Field example_id must be a string');
      }
    }

    // Required field: version_tag
    if (!('version_tag' in data)) {
      errors.push('Missing required field: version_tag');
    } else {
      if (typeof data.version_tag !== 'string') {
        errors.push('Field version_tag must be a string');
      }
    }

    // Required field: version_number
    if (!('version_number' in data)) {
      errors.push('Missing required field: version_number');
    } else {
      if (typeof data.version_number !== 'number') {
        errors.push('Field version_number must be a number');
      }
    }

    // Required field: storage_path
    if (!('storage_path' in data)) {
      errors.push('Missing required field: storage_path');
    } else {
      if (typeof data.storage_path !== 'string') {
        errors.push('Field storage_path must be a string');
      }
    }

    // Required field: meta_yaml
    if (!('meta_yaml' in data)) {
      errors.push('Missing required field: meta_yaml');
    } else {
      if (typeof data.meta_yaml !== 'string') {
        errors.push('Field meta_yaml must be a string');
      }
    }

    // Optional field: test_yaml
    if ('test_yaml' in data && data.test_yaml !== undefined && data.test_yaml !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleVersionGet', errors.join('; '));
    }

    return data as ExampleVersionGet;
  }

  safeValidate(data: any): { success: true; data: ExampleVersionGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleVersionGet', String(error)) };
    }
  }
}

/**
 * List view of example versions.
 */
export class ExampleVersionListValidator extends BaseValidator<ExampleVersionList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "List view of example versions.",
  "properties": {
    "id": {
      "title": "Id",
      "type": "string"
    },
    "version_tag": {
      "title": "Version Tag",
      "type": "string"
    },
    "version_number": {
      "title": "Version Number",
      "type": "integer"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    }
  },
  "required": [
    "id",
    "version_tag",
    "version_number",
    "created_at"
  ],
  "title": "ExampleVersionList",
  "type": "object",
  "x-model-name": "ExampleVersionList"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleVersionList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleVersionList', 'Expected an object');
    }

    // Required field: id
    if (!('id' in data)) {
      errors.push('Missing required field: id');
    } else {
      if (typeof data.id !== 'string') {
        errors.push('Field id must be a string');
      }
    }

    // Required field: version_tag
    if (!('version_tag' in data)) {
      errors.push('Missing required field: version_tag');
    } else {
      if (typeof data.version_tag !== 'string') {
        errors.push('Field version_tag must be a string');
      }
    }

    // Required field: version_number
    if (!('version_number' in data)) {
      errors.push('Missing required field: version_number');
    } else {
      if (typeof data.version_number !== 'number') {
        errors.push('Field version_number must be a number');
      }
    }

    // Required field: created_at
    if (!('created_at' in data)) {
      errors.push('Missing required field: created_at');
    } else {
      if (typeof data.created_at !== 'string') {
        errors.push('Field created_at must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleVersionList', errors.join('; '));
    }

    return data as ExampleVersionList;
  }

  safeValidate(data: any): { success: true; data: ExampleVersionList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleVersionList', String(error)) };
    }
  }
}

/**
 * Query parameters for listing example versions (filtering).
 */
export class ExampleVersionQueryValidator extends BaseValidator<ExampleVersionQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Query parameters for listing example versions (filtering).",
  "properties": {
    "skip": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": 0,
      "title": "Skip"
    },
    "limit": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": 100,
      "title": "Limit"
    },
    "version_tag": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Version Tag"
    }
  },
  "title": "ExampleVersionQuery",
  "type": "object",
  "x-model-name": "ExampleVersionQuery"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleVersionQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleVersionQuery', 'Expected an object');
    }

    // Optional field: skip
    if ('skip' in data && data.skip !== undefined && data.skip !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: limit
    if ('limit' in data && data.limit !== undefined && data.limit !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: version_tag
    if ('version_tag' in data && data.version_tag !== undefined && data.version_tag !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleVersionQuery', errors.join('; '));
    }

    return data as ExampleVersionQuery;
  }

  safeValidate(data: any): { success: true; data: ExampleVersionQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleVersionQuery', String(error)) };
    }
  }
}

/**
 * Create example dependency.
 */
export class ExampleDependencyCreateValidator extends BaseValidator<ExampleDependencyCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Create example dependency.",
  "properties": {
    "example_id": {
      "title": "Example Id",
      "type": "string"
    },
    "depends_id": {
      "title": "Depends Id",
      "type": "string"
    },
    "version_constraint": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Version constraint (e.g., '>=1.2.0', '^2.1.0'). NULL means latest version.",
      "title": "Version Constraint"
    }
  },
  "required": [
    "example_id",
    "depends_id"
  ],
  "title": "ExampleDependencyCreate",
  "type": "object",
  "x-model-name": "ExampleDependencyCreate"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleDependencyCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleDependencyCreate', 'Expected an object');
    }

    // Required field: example_id
    if (!('example_id' in data)) {
      errors.push('Missing required field: example_id');
    } else {
      if (typeof data.example_id !== 'string') {
        errors.push('Field example_id must be a string');
      }
    }

    // Required field: depends_id
    if (!('depends_id' in data)) {
      errors.push('Missing required field: depends_id');
    } else {
      if (typeof data.depends_id !== 'string') {
        errors.push('Field depends_id must be a string');
      }
    }

    // Optional field: version_constraint
    if ('version_constraint' in data && data.version_constraint !== undefined && data.version_constraint !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleDependencyCreate', errors.join('; '));
    }

    return data as ExampleDependencyCreate;
  }

  safeValidate(data: any): { success: true; data: ExampleDependencyCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleDependencyCreate', String(error)) };
    }
  }
}

/**
 * Get example dependency details.
 */
export class ExampleDependencyGetValidator extends BaseValidator<ExampleDependencyGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "ExampleList": {
      "description": "List view of examples.",
      "properties": {
        "created_at": {
          "anyOf": [
            {
              "format": "date-time",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Creation timestamp",
          "title": "Created At"
        },
        "updated_at": {
          "anyOf": [
            {
              "format": "date-time",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Update timestamp",
          "title": "Updated At"
        },
        "id": {
          "title": "Id",
          "type": "string"
        },
        "directory": {
          "title": "Directory",
          "type": "string"
        },
        "identifier": {
          "title": "Identifier",
          "type": "string"
        },
        "title": {
          "title": "Title",
          "type": "string"
        },
        "subject": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Subject"
        },
        "category": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Category"
        },
        "tags": {
          "default": [],
          "items": {
            "type": "string"
          },
          "title": "Tags",
          "type": "array"
        },
        "example_repository_id": {
          "title": "Example Repository Id",
          "type": "string"
        }
      },
      "required": [
        "id",
        "directory",
        "identifier",
        "title",
        "example_repository_id"
      ],
      "title": "ExampleList",
      "type": "object"
    }
  },
  "description": "Get example dependency details.",
  "properties": {
    "id": {
      "title": "Id",
      "type": "string"
    },
    "example_id": {
      "title": "Example Id",
      "type": "string"
    },
    "depends_id": {
      "title": "Depends Id",
      "type": "string"
    },
    "version_constraint": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Version constraint string",
      "title": "Version Constraint"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "dependency": {
      "anyOf": [
        {
          "$ref": "#/$defs/ExampleList"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "required": [
    "id",
    "example_id",
    "depends_id",
    "created_at"
  ],
  "title": "ExampleDependencyGet",
  "type": "object",
  "x-model-name": "ExampleDependencyGet"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleDependencyGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleDependencyGet', 'Expected an object');
    }

    // Required field: id
    if (!('id' in data)) {
      errors.push('Missing required field: id');
    } else {
      if (typeof data.id !== 'string') {
        errors.push('Field id must be a string');
      }
    }

    // Required field: example_id
    if (!('example_id' in data)) {
      errors.push('Missing required field: example_id');
    } else {
      if (typeof data.example_id !== 'string') {
        errors.push('Field example_id must be a string');
      }
    }

    // Required field: depends_id
    if (!('depends_id' in data)) {
      errors.push('Missing required field: depends_id');
    } else {
      if (typeof data.depends_id !== 'string') {
        errors.push('Field depends_id must be a string');
      }
    }

    // Optional field: version_constraint
    if ('version_constraint' in data && data.version_constraint !== undefined && data.version_constraint !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: created_at
    if (!('created_at' in data)) {
      errors.push('Missing required field: created_at');
    } else {
      if (typeof data.created_at !== 'string') {
        errors.push('Field created_at must be a string');
      }
    }

    // Optional field: dependency
    if ('dependency' in data && data.dependency !== undefined && data.dependency !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleDependencyGet', errors.join('; '));
    }

    return data as ExampleDependencyGet;
  }

  safeValidate(data: any): { success: true; data: ExampleDependencyGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleDependencyGet', String(error)) };
    }
  }
}

/**
 * Query parameters for listing examples.
 */
export class ExampleQueryValidator extends BaseValidator<ExampleQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Query parameters for listing examples.",
  "properties": {
    "skip": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": 0,
      "title": "Skip"
    },
    "limit": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": 100,
      "title": "Limit"
    },
    "repository_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Repository Id"
    },
    "identifier": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Filter by identifier (supports Ltree patterns with *)",
      "title": "Identifier"
    },
    "title": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Title"
    },
    "category": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Category"
    },
    "tags": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Tags"
    },
    "search": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Search"
    }
  },
  "title": "ExampleQuery",
  "type": "object",
  "x-model-name": "ExampleQuery"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleQuery', 'Expected an object');
    }

    // Optional field: skip
    if ('skip' in data && data.skip !== undefined && data.skip !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: limit
    if ('limit' in data && data.limit !== undefined && data.limit !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: repository_id
    if ('repository_id' in data && data.repository_id !== undefined && data.repository_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: identifier
    if ('identifier' in data && data.identifier !== undefined && data.identifier !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: category
    if ('category' in data && data.category !== undefined && data.category !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: tags
    if ('tags' in data && data.tags !== undefined && data.tags !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: search
    if ('search' in data && data.search !== undefined && data.search !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleQuery', errors.join('; '));
    }

    return data as ExampleQuery;
  }

  safeValidate(data: any): { success: true; data: ExampleQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleQuery', String(error)) };
    }
  }
}

/**
 * Query parameters for listing repositories.
 */
export class ExampleRepositoryQueryValidator extends BaseValidator<ExampleRepositoryQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Query parameters for listing repositories.",
  "properties": {
    "skip": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": 0,
      "title": "Skip"
    },
    "limit": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": 100,
      "title": "Limit"
    },
    "name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Name"
    },
    "source_type": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Source Type"
    },
    "organization_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Organization Id"
    }
  },
  "title": "ExampleRepositoryQuery",
  "type": "object",
  "x-model-name": "ExampleRepositoryQuery"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleRepositoryQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleRepositoryQuery', 'Expected an object');
    }

    // Optional field: skip
    if ('skip' in data && data.skip !== undefined && data.skip !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: limit
    if ('limit' in data && data.limit !== undefined && data.limit !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: name
    if ('name' in data && data.name !== undefined && data.name !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: source_type
    if ('source_type' in data && data.source_type !== undefined && data.source_type !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: organization_id
    if ('organization_id' in data && data.organization_id !== undefined && data.organization_id !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleRepositoryQuery', errors.join('; '));
    }

    return data as ExampleRepositoryQuery;
  }

  safeValidate(data: any): { success: true; data: ExampleRepositoryQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleRepositoryQuery', String(error)) };
    }
  }
}

/**
 * Request to upload an example to storage.
 */
export class ExampleUploadRequestValidator extends BaseValidator<ExampleUploadRequest> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Request to upload an example to storage.",
  "properties": {
    "repository_id": {
      "title": "Repository Id",
      "type": "string"
    },
    "directory": {
      "pattern": "^[a-zA-Z0-9._-]+$",
      "title": "Directory",
      "type": "string"
    },
    "files": {
      "additionalProperties": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "format": "binary",
            "type": "string"
          }
        ]
      },
      "description": "Map of filename to content. Text files as UTF-8 strings, binary files as either base64-encoded strings or raw bytes. Must include meta.yaml",
      "title": "Files",
      "type": "object"
    }
  },
  "required": [
    "repository_id",
    "directory",
    "files"
  ],
  "title": "ExampleUploadRequest",
  "type": "object",
  "x-model-name": "ExampleUploadRequest"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleUploadRequest {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleUploadRequest', 'Expected an object');
    }

    // Required field: repository_id
    if (!('repository_id' in data)) {
      errors.push('Missing required field: repository_id');
    } else {
      if (typeof data.repository_id !== 'string') {
        errors.push('Field repository_id must be a string');
      }
    }

    // Required field: directory
    if (!('directory' in data)) {
      errors.push('Missing required field: directory');
    } else {
      if (typeof data.directory !== 'string') {
        errors.push('Field directory must be a string');
      }
    }

    // Required field: files
    if (!('files' in data)) {
      errors.push('Missing required field: files');
    } else {
      if (typeof data.files !== 'object' || data.files === null) {
        errors.push('Field files must be an object');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleUploadRequest', errors.join('; '));
    }

    return data as ExampleUploadRequest;
  }

  safeValidate(data: any): { success: true; data: ExampleUploadRequest } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleUploadRequest', String(error)) };
    }
  }
}

/**
 * Request to upload multiple examples to storage.
 */
export class ExampleBatchUploadRequestValidator extends BaseValidator<ExampleBatchUploadRequest> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Request to upload multiple examples to storage.",
  "properties": {
    "repository_id": {
      "title": "Repository Id",
      "type": "string"
    },
    "examples": {
      "description": "List of examples with directory and files",
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "title": "Examples",
      "type": "array"
    }
  },
  "required": [
    "repository_id",
    "examples"
  ],
  "title": "ExampleBatchUploadRequest",
  "type": "object",
  "x-model-name": "ExampleBatchUploadRequest"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleBatchUploadRequest {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleBatchUploadRequest', 'Expected an object');
    }

    // Required field: repository_id
    if (!('repository_id' in data)) {
      errors.push('Missing required field: repository_id');
    } else {
      if (typeof data.repository_id !== 'string') {
        errors.push('Field repository_id must be a string');
      }
    }

    // Required field: examples
    if (!('examples' in data)) {
      errors.push('Missing required field: examples');
    } else {
      if (!Array.isArray(data.examples)) {
        errors.push('Field examples must be an array');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleBatchUploadRequest', errors.join('; '));
    }

    return data as ExampleBatchUploadRequest;
  }

  safeValidate(data: any): { success: true; data: ExampleBatchUploadRequest } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleBatchUploadRequest', String(error)) };
    }
  }
}

/**
 * Files for a single example.
 */
export class ExampleFileSetValidator extends BaseValidator<ExampleFileSet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Files for a single example.",
  "properties": {
    "example_id": {
      "title": "Example Id",
      "type": "string"
    },
    "version_id": {
      "title": "Version Id",
      "type": "string"
    },
    "version_tag": {
      "title": "Version Tag",
      "type": "string"
    },
    "directory": {
      "title": "Directory",
      "type": "string"
    },
    "identifier": {
      "title": "Identifier",
      "type": "string"
    },
    "title": {
      "title": "Title",
      "type": "string"
    },
    "files": {
      "additionalProperties": {
        "type": "string"
      },
      "description": "Map of filename to content",
      "title": "Files",
      "type": "object"
    },
    "meta_yaml": {
      "title": "Meta Yaml",
      "type": "string"
    },
    "test_yaml": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Test Yaml"
    }
  },
  "required": [
    "example_id",
    "version_id",
    "version_tag",
    "directory",
    "identifier",
    "title",
    "files",
    "meta_yaml"
  ],
  "title": "ExampleFileSet",
  "type": "object",
  "x-model-name": "ExampleFileSet"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleFileSet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleFileSet', 'Expected an object');
    }

    // Required field: example_id
    if (!('example_id' in data)) {
      errors.push('Missing required field: example_id');
    } else {
      if (typeof data.example_id !== 'string') {
        errors.push('Field example_id must be a string');
      }
    }

    // Required field: version_id
    if (!('version_id' in data)) {
      errors.push('Missing required field: version_id');
    } else {
      if (typeof data.version_id !== 'string') {
        errors.push('Field version_id must be a string');
      }
    }

    // Required field: version_tag
    if (!('version_tag' in data)) {
      errors.push('Missing required field: version_tag');
    } else {
      if (typeof data.version_tag !== 'string') {
        errors.push('Field version_tag must be a string');
      }
    }

    // Required field: directory
    if (!('directory' in data)) {
      errors.push('Missing required field: directory');
    } else {
      if (typeof data.directory !== 'string') {
        errors.push('Field directory must be a string');
      }
    }

    // Required field: identifier
    if (!('identifier' in data)) {
      errors.push('Missing required field: identifier');
    } else {
      if (typeof data.identifier !== 'string') {
        errors.push('Field identifier must be a string');
      }
    }

    // Required field: title
    if (!('title' in data)) {
      errors.push('Missing required field: title');
    } else {
      if (typeof data.title !== 'string') {
        errors.push('Field title must be a string');
      }
    }

    // Required field: files
    if (!('files' in data)) {
      errors.push('Missing required field: files');
    } else {
      if (typeof data.files !== 'object' || data.files === null) {
        errors.push('Field files must be an object');
      }
    }

    // Required field: meta_yaml
    if (!('meta_yaml' in data)) {
      errors.push('Missing required field: meta_yaml');
    } else {
      if (typeof data.meta_yaml !== 'string') {
        errors.push('Field meta_yaml must be a string');
      }
    }

    // Optional field: test_yaml
    if ('test_yaml' in data && data.test_yaml !== undefined && data.test_yaml !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleFileSet', errors.join('; '));
    }

    return data as ExampleFileSet;
  }

  safeValidate(data: any): { success: true; data: ExampleFileSet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleFileSet', String(error)) };
    }
  }
}

/**
 * Response containing downloaded example files.
 */
export class ExampleDownloadResponseValidator extends BaseValidator<ExampleDownloadResponse> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "ExampleFileSet": {
      "description": "Files for a single example.",
      "properties": {
        "example_id": {
          "title": "Example Id",
          "type": "string"
        },
        "version_id": {
          "title": "Version Id",
          "type": "string"
        },
        "version_tag": {
          "title": "Version Tag",
          "type": "string"
        },
        "directory": {
          "title": "Directory",
          "type": "string"
        },
        "identifier": {
          "title": "Identifier",
          "type": "string"
        },
        "title": {
          "title": "Title",
          "type": "string"
        },
        "files": {
          "additionalProperties": {
            "type": "string"
          },
          "description": "Map of filename to content",
          "title": "Files",
          "type": "object"
        },
        "meta_yaml": {
          "title": "Meta Yaml",
          "type": "string"
        },
        "test_yaml": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Test Yaml"
        }
      },
      "required": [
        "example_id",
        "version_id",
        "version_tag",
        "directory",
        "identifier",
        "title",
        "files",
        "meta_yaml"
      ],
      "title": "ExampleFileSet",
      "type": "object"
    }
  },
  "description": "Response containing downloaded example files.",
  "properties": {
    "example_id": {
      "title": "Example Id",
      "type": "string"
    },
    "version_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Version Id"
    },
    "version_tag": {
      "title": "Version Tag",
      "type": "string"
    },
    "files": {
      "additionalProperties": {
        "type": "string"
      },
      "description": "Map of filename to content",
      "title": "Files",
      "type": "object"
    },
    "meta_yaml": {
      "title": "Meta Yaml",
      "type": "string"
    },
    "test_yaml": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Test Yaml"
    },
    "dependencies": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/ExampleFileSet"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Dependency examples when with_dependencies=True",
      "title": "Dependencies"
    }
  },
  "required": [
    "example_id",
    "version_tag",
    "files",
    "meta_yaml"
  ],
  "title": "ExampleDownloadResponse",
  "type": "object",
  "x-model-name": "ExampleDownloadResponse"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExampleDownloadResponse {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExampleDownloadResponse', 'Expected an object');
    }

    // Required field: example_id
    if (!('example_id' in data)) {
      errors.push('Missing required field: example_id');
    } else {
      if (typeof data.example_id !== 'string') {
        errors.push('Field example_id must be a string');
      }
    }

    // Optional field: version_id
    if ('version_id' in data && data.version_id !== undefined && data.version_id !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: version_tag
    if (!('version_tag' in data)) {
      errors.push('Missing required field: version_tag');
    } else {
      if (typeof data.version_tag !== 'string') {
        errors.push('Field version_tag must be a string');
      }
    }

    // Required field: files
    if (!('files' in data)) {
      errors.push('Missing required field: files');
    } else {
      if (typeof data.files !== 'object' || data.files === null) {
        errors.push('Field files must be an object');
      }
    }

    // Required field: meta_yaml
    if (!('meta_yaml' in data)) {
      errors.push('Missing required field: meta_yaml');
    } else {
      if (typeof data.meta_yaml !== 'string') {
        errors.push('Field meta_yaml must be a string');
      }
    }

    // Optional field: test_yaml
    if ('test_yaml' in data && data.test_yaml !== undefined && data.test_yaml !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: dependencies
    if ('dependencies' in data && data.dependencies !== undefined && data.dependencies !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ExampleDownloadResponse', errors.join('; '));
    }

    return data as ExampleDownloadResponse;
  }

  safeValidate(data: any): { success: true; data: ExampleDownloadResponse } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExampleDownloadResponse', String(error)) };
    }
  }
}

/**
 * Validator for ExamplesUploadConfig
 */
export class ExamplesUploadConfigValidator extends BaseValidator<ExamplesUploadConfig> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "repository": {
      "description": "Name of the Example Repository to use/create",
      "title": "Repository",
      "type": "string"
    },
    "path": {
      "description": "Relative path to directory containing example subdirectories",
      "title": "Path",
      "type": "string"
    }
  },
  "required": [
    "repository",
    "path"
  ],
  "title": "ExamplesUploadConfig",
  "type": "object",
  "x-model-name": "ExamplesUploadConfig"
}`);
    }
    return this._schema;
  }

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.getSchema().properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.getSchema().required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.getSchema().required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.getSchema().properties ?? {});
  }

  validate(data: any): ExamplesUploadConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ExamplesUploadConfig', 'Expected an object');
    }

    // Required field: repository
    if (!('repository' in data)) {
      errors.push('Missing required field: repository');
    } else {
      if (typeof data.repository !== 'string') {
        errors.push('Field repository must be a string');
      }
    }

    // Required field: path
    if (!('path' in data)) {
      errors.push('Missing required field: path');
    } else {
      if (typeof data.path !== 'string') {
        errors.push('Field path must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('ExamplesUploadConfig', errors.join('; '));
    }

    return data as ExamplesUploadConfig;
  }

  safeValidate(data: any): { success: true; data: ExamplesUploadConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ExamplesUploadConfig', String(error)) };
    }
  }
}
