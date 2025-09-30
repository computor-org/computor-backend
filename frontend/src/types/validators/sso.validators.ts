/**
 * Auto-generated validation classes for Sso models
 * DO NOT EDIT MANUALLY
 */

import type { ProviderInfo } from '../generated/sso';
import { BaseValidator, ValidationError } from './BaseValidator';

/**
 * Information about an authentication provider.
 */
export class ProviderInfoValidator extends BaseValidator<ProviderInfo> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "description": "Information about an authentication provider.",
  "properties": {
    "name": {
      "description": "Provider name",
      "title": "Name",
      "type": "string"
    },
    "display_name": {
      "description": "Display name",
      "title": "Display Name",
      "type": "string"
    },
    "type": {
      "description": "Authentication type",
      "title": "Type",
      "type": "string"
    },
    "enabled": {
      "description": "Whether provider is enabled",
      "title": "Enabled",
      "type": "boolean"
    },
    "login_url": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Login URL if applicable",
      "title": "Login Url"
    }
  },
  "required": [
    "name",
    "display_name",
    "type",
    "enabled"
  ],
  "title": "ProviderInfo",
  "type": "object",
  "x-model-name": "ProviderInfo"
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

  validate(data: any): ProviderInfo {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ProviderInfo', 'Expected an object');
    }

    // Required field: name
    if (!('name' in data)) {
      errors.push('Missing required field: name');
    } else {
      if (typeof data.name !== 'string') {
        errors.push('Field name must be a string');
      }
    }

    // Required field: display_name
    if (!('display_name' in data)) {
      errors.push('Missing required field: display_name');
    } else {
      if (typeof data.display_name !== 'string') {
        errors.push('Field display_name must be a string');
      }
    }

    // Required field: type
    if (!('type' in data)) {
      errors.push('Missing required field: type');
    } else {
      if (typeof data.type !== 'string') {
        errors.push('Field type must be a string');
      }
    }

    // Required field: enabled
    if (!('enabled' in data)) {
      errors.push('Missing required field: enabled');
    } else {
      if (typeof data.enabled !== 'boolean') {
        errors.push('Field enabled must be a boolean');
      }
    }

    // Optional field: login_url
    if ('login_url' in data && data.login_url !== undefined && data.login_url !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ProviderInfo', errors.join('; '));
    }

    return data as ProviderInfo;
  }

  safeValidate(data: any): { success: true; data: ProviderInfo } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ProviderInfo', String(error)) };
    }
  }
}
