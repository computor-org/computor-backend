/**
 * Auto-generated validation classes for Roles models
 * DO NOT EDIT MANUALLY
 */

import type { RoleClaimGet, RoleClaimList, RoleClaimQuery, RoleGet, RoleList, RoleQuery } from '../generated/roles';
import { BaseValidator, ValidationError } from './BaseValidator';

/**
 * Validator for RoleGet
 */
export class RoleGetValidator extends BaseValidator<RoleGet> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "properties": {
    "id": {
      "description": "Role unique identifier",
      "title": "Id",
      "type": "string"
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
      "description": "Role title",
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
      "description": "Role description",
      "title": "Description"
    },
    "builtin": {
      "description": "Whether this is a built-in role",
      "title": "Builtin",
      "type": "boolean"
    }
  },
  "required": [
    "id",
    "builtin"
  ],
  "title": "RoleGet",
  "type": "object",
  "x-model-name": "RoleGet"
}`) as const;

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.schema.properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.schema.required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.schema.required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.schema.properties ?? {});
  }

  validate(data: any): RoleGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('RoleGet', 'Expected an object');
    }

    // Required field: id
    if (!('id' in data)) {
      errors.push('Missing required field: id');
    } else {
      if (typeof data.id !== 'string') {
        errors.push('Field id must be a string');
      }
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: builtin
    if (!('builtin' in data)) {
      errors.push('Missing required field: builtin');
    } else {
      if (typeof data.builtin !== 'boolean') {
        errors.push('Field builtin must be a boolean');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('RoleGet', errors.join('; '));
    }

    return data as RoleGet;
  }

  safeValidate(data: any): { success: true; data: RoleGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('RoleGet', String(error)) };
    }
  }
}

/**
 * Validator for RoleList
 */
export class RoleListValidator extends BaseValidator<RoleList> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "properties": {
    "id": {
      "description": "Role unique identifier",
      "title": "Id",
      "type": "string"
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
      "description": "Role title",
      "title": "Title"
    },
    "builtin": {
      "description": "Whether this is a built-in role",
      "title": "Builtin",
      "type": "boolean"
    }
  },
  "required": [
    "id",
    "builtin"
  ],
  "title": "RoleList",
  "type": "object",
  "x-model-name": "RoleList"
}`) as const;

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.schema.properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.schema.required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.schema.required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.schema.properties ?? {});
  }

  validate(data: any): RoleList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('RoleList', 'Expected an object');
    }

    // Required field: id
    if (!('id' in data)) {
      errors.push('Missing required field: id');
    } else {
      if (typeof data.id !== 'string') {
        errors.push('Field id must be a string');
      }
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: builtin
    if (!('builtin' in data)) {
      errors.push('Missing required field: builtin');
    } else {
      if (typeof data.builtin !== 'boolean') {
        errors.push('Field builtin must be a boolean');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('RoleList', errors.join('; '));
    }

    return data as RoleList;
  }

  safeValidate(data: any): { success: true; data: RoleList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('RoleList', String(error)) };
    }
  }
}

/**
 * Validator for RoleQuery
 */
export class RoleQueryValidator extends BaseValidator<RoleQuery> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
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
    "id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Filter by role ID",
      "title": "Id"
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
      "description": "Filter by role title",
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
      "description": "Filter by description",
      "title": "Description"
    },
    "builtin": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Filter by builtin status",
      "title": "Builtin"
    }
  },
  "title": "RoleQuery",
  "type": "object",
  "x-model-name": "RoleQuery"
}`) as const;

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.schema.properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.schema.required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.schema.required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.schema.properties ?? {});
  }

  validate(data: any): RoleQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('RoleQuery', 'Expected an object');
    }

    // Optional field: skip
    if ('skip' in data && data.skip !== undefined && data.skip !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: limit
    if ('limit' in data && data.limit !== undefined && data.limit !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: id
    if ('id' in data && data.id !== undefined && data.id !== null) {
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

    // Optional field: builtin
    if ('builtin' in data && data.builtin !== undefined && data.builtin !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('RoleQuery', errors.join('; '));
    }

    return data as RoleQuery;
  }

  safeValidate(data: any): { success: true; data: RoleQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('RoleQuery', String(error)) };
    }
  }
}

/**
 * Validator for RoleClaimGet
 */
export class RoleClaimGetValidator extends BaseValidator<RoleClaimGet> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "properties": {
    "role_id": {
      "title": "Role Id",
      "type": "string"
    },
    "claim_type": {
      "title": "Claim Type",
      "type": "string"
    },
    "claim_value": {
      "title": "Claim Value",
      "type": "string"
    },
    "properties": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Properties"
    }
  },
  "required": [
    "role_id",
    "claim_type",
    "claim_value"
  ],
  "title": "RoleClaimGet",
  "type": "object",
  "x-model-name": "RoleClaimGet"
}`) as const;

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.schema.properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.schema.required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.schema.required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.schema.properties ?? {});
  }

  validate(data: any): RoleClaimGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('RoleClaimGet', 'Expected an object');
    }

    // Required field: role_id
    if (!('role_id' in data)) {
      errors.push('Missing required field: role_id');
    } else {
      if (typeof data.role_id !== 'string') {
        errors.push('Field role_id must be a string');
      }
    }

    // Required field: claim_type
    if (!('claim_type' in data)) {
      errors.push('Missing required field: claim_type');
    } else {
      if (typeof data.claim_type !== 'string') {
        errors.push('Field claim_type must be a string');
      }
    }

    // Required field: claim_value
    if (!('claim_value' in data)) {
      errors.push('Missing required field: claim_value');
    } else {
      if (typeof data.claim_value !== 'string') {
        errors.push('Field claim_value must be a string');
      }
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('RoleClaimGet', errors.join('; '));
    }

    return data as RoleClaimGet;
  }

  safeValidate(data: any): { success: true; data: RoleClaimGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('RoleClaimGet', String(error)) };
    }
  }
}

/**
 * Validator for RoleClaimList
 */
export class RoleClaimListValidator extends BaseValidator<RoleClaimList> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "properties": {
    "role_id": {
      "title": "Role Id",
      "type": "string"
    },
    "claim_type": {
      "title": "Claim Type",
      "type": "string"
    },
    "claim_value": {
      "title": "Claim Value",
      "type": "string"
    }
  },
  "required": [
    "role_id",
    "claim_type",
    "claim_value"
  ],
  "title": "RoleClaimList",
  "type": "object",
  "x-model-name": "RoleClaimList"
}`) as const;

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.schema.properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.schema.required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.schema.required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.schema.properties ?? {});
  }

  validate(data: any): RoleClaimList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('RoleClaimList', 'Expected an object');
    }

    // Required field: role_id
    if (!('role_id' in data)) {
      errors.push('Missing required field: role_id');
    } else {
      if (typeof data.role_id !== 'string') {
        errors.push('Field role_id must be a string');
      }
    }

    // Required field: claim_type
    if (!('claim_type' in data)) {
      errors.push('Missing required field: claim_type');
    } else {
      if (typeof data.claim_type !== 'string') {
        errors.push('Field claim_type must be a string');
      }
    }

    // Required field: claim_value
    if (!('claim_value' in data)) {
      errors.push('Missing required field: claim_value');
    } else {
      if (typeof data.claim_value !== 'string') {
        errors.push('Field claim_value must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('RoleClaimList', errors.join('; '));
    }

    return data as RoleClaimList;
  }

  safeValidate(data: any): { success: true; data: RoleClaimList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('RoleClaimList', String(error)) };
    }
  }
}

/**
 * Validator for RoleClaimQuery
 */
export class RoleClaimQueryValidator extends BaseValidator<RoleClaimQuery> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
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
    "role_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Role Id"
    },
    "claim_type": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Claim Type"
    },
    "claim_value": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Claim Value"
    }
  },
  "title": "RoleClaimQuery",
  "type": "object",
  "x-model-name": "RoleClaimQuery"
}`) as const;

  /**
   * Get schema for a specific field
   */
  static getFieldSchema(fieldName: string): any {
    return this.schema.properties?.[fieldName];
  }

  /**
   * Check if a field is required
   */
  static isFieldRequired(fieldName: string): boolean {
    return this.schema.required?.includes(fieldName) ?? false;
  }

  /**
   * Get all required field names
   */
  static getRequiredFields(): string[] {
    return this.schema.required ?? [];
  }

  /**
   * Get all field names
   */
  static getFields(): string[] {
    return Object.keys(this.schema.properties ?? {});
  }

  validate(data: any): RoleClaimQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('RoleClaimQuery', 'Expected an object');
    }

    // Optional field: skip
    if ('skip' in data && data.skip !== undefined && data.skip !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: limit
    if ('limit' in data && data.limit !== undefined && data.limit !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: role_id
    if ('role_id' in data && data.role_id !== undefined && data.role_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: claim_type
    if ('claim_type' in data && data.claim_type !== undefined && data.claim_type !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: claim_value
    if ('claim_value' in data && data.claim_value !== undefined && data.claim_value !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('RoleClaimQuery', errors.join('; '));
    }

    return data as RoleClaimQuery;
  }

  safeValidate(data: any): { success: true; data: RoleClaimQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('RoleClaimQuery', String(error)) };
    }
  }
}
