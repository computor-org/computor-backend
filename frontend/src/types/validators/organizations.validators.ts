/**
 * Auto-generated validation classes for Organizations models
 * DO NOT EDIT MANUALLY
 */

import type { HierarchicalOrganizationConfig, OrganizationConfig, OrganizationCreate, OrganizationGet, OrganizationList, OrganizationProperties, OrganizationPropertiesGet, OrganizationQuery, OrganizationTaskRequest, OrganizationUpdate } from '../generated/organizations';
import { OrganizationType } from '../generated/organizations';
import { BaseValidator, ValidationError } from './BaseValidator';

export function validateOrganizationType(value: any): OrganizationType {
  const validValues = ['user', 'community', 'organization'];
  if (!validValues.includes(value)) {
    throw new ValidationError('OrganizationType', `Invalid value: ${value}. Expected one of: ${validValues.join(', ')}`);
  }
  return value as OrganizationType;
}

/**
 * Validator for OrganizationProperties
 */
export class OrganizationPropertiesValidator extends BaseValidator<OrganizationProperties> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "GitLabConfig": {
      "properties": {
        "settings": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "title": "Settings"
        },
        "url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Url"
        },
        "full_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path"
        },
        "directory": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Directory"
        },
        "registry": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Registry"
        },
        "parent": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Parent"
        },
        "group_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Group Id"
        },
        "parent_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Parent Id"
        },
        "namespace_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Namespace Id"
        },
        "namespace_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Namespace Path"
        },
        "web_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Web Url"
        },
        "visibility": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Visibility"
        },
        "last_synced_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Last Synced At"
        },
        "token": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Token"
        }
      },
      "title": "GitLabConfig",
      "type": "object"
    }
  },
  "additionalProperties": true,
  "properties": {
    "gitlab": {
      "anyOf": [
        {
          "$ref": "#/$defs/GitLabConfig"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "title": "OrganizationProperties",
  "type": "object",
  "x-model-name": "OrganizationProperties"
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

  validate(data: any): OrganizationProperties {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('OrganizationProperties', 'Expected an object');
    }

    // Optional field: gitlab
    if ('gitlab' in data && data.gitlab !== undefined && data.gitlab !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('OrganizationProperties', errors.join('; '));
    }

    return data as OrganizationProperties;
  }

  safeValidate(data: any): { success: true; data: OrganizationProperties } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('OrganizationProperties', String(error)) };
    }
  }
}

/**
 * Validator for OrganizationPropertiesGet
 */
export class OrganizationPropertiesGetValidator extends BaseValidator<OrganizationPropertiesGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "GitLabConfigGet": {
      "properties": {
        "settings": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "title": "Settings"
        },
        "url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Url"
        },
        "full_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path"
        },
        "directory": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Directory"
        },
        "registry": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Registry"
        },
        "parent": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Parent"
        },
        "group_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Group Id"
        },
        "parent_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Parent Id"
        },
        "namespace_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Namespace Id"
        },
        "namespace_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Namespace Path"
        },
        "web_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Web Url"
        },
        "visibility": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Visibility"
        },
        "last_synced_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Last Synced At"
        }
      },
      "title": "GitLabConfigGet",
      "type": "object"
    }
  },
  "additionalProperties": true,
  "properties": {
    "gitlab": {
      "anyOf": [
        {
          "$ref": "#/$defs/GitLabConfigGet"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "title": "OrganizationPropertiesGet",
  "type": "object",
  "x-model-name": "OrganizationPropertiesGet"
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

  validate(data: any): OrganizationPropertiesGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('OrganizationPropertiesGet', 'Expected an object');
    }

    // Optional field: gitlab
    if ('gitlab' in data && data.gitlab !== undefined && data.gitlab !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('OrganizationPropertiesGet', errors.join('; '));
    }

    return data as OrganizationPropertiesGet;
  }

  safeValidate(data: any): { success: true; data: OrganizationPropertiesGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('OrganizationPropertiesGet', String(error)) };
    }
  }
}

/**
 * Validator for OrganizationCreate
 */
export class OrganizationCreateValidator extends BaseValidator<OrganizationCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "GitLabConfig": {
      "properties": {
        "settings": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "title": "Settings"
        },
        "url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Url"
        },
        "full_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path"
        },
        "directory": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Directory"
        },
        "registry": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Registry"
        },
        "parent": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Parent"
        },
        "group_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Group Id"
        },
        "parent_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Parent Id"
        },
        "namespace_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Namespace Id"
        },
        "namespace_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Namespace Path"
        },
        "web_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Web Url"
        },
        "visibility": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Visibility"
        },
        "last_synced_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Last Synced At"
        },
        "token": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Token"
        }
      },
      "title": "GitLabConfig",
      "type": "object"
    },
    "OrganizationProperties": {
      "additionalProperties": true,
      "properties": {
        "gitlab": {
          "anyOf": [
            {
              "$ref": "#/$defs/GitLabConfig"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "OrganizationProperties",
      "type": "object"
    },
    "OrganizationType": {
      "enum": [
        "user",
        "community",
        "organization"
      ],
      "title": "OrganizationType",
      "type": "string"
    }
  },
  "properties": {
    "title": {
      "anyOf": [
        {
          "maxLength": 255,
          "minLength": 1,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Organization title",
      "title": "Title"
    },
    "description": {
      "anyOf": [
        {
          "maxLength": 4096,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Organization description",
      "title": "Description"
    },
    "path": {
      "description": "Hierarchical path (ltree format)",
      "minLength": 1,
      "title": "Path",
      "type": "string"
    },
    "organization_type": {
      "$ref": "#/$defs/OrganizationType",
      "description": "Type of organization"
    },
    "user_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Associated user ID (for user type organizations)",
      "title": "User Id"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/OrganizationProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Additional properties"
    },
    "number": {
      "anyOf": [
        {
          "maxLength": 255,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Organization number/identifier",
      "title": "Number"
    },
    "email": {
      "anyOf": [
        {
          "format": "email",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Contact email address",
      "title": "Email"
    },
    "telephone": {
      "anyOf": [
        {
          "maxLength": 255,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Phone number",
      "title": "Telephone"
    },
    "fax_number": {
      "anyOf": [
        {
          "maxLength": 255,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Fax number",
      "title": "Fax Number"
    },
    "url": {
      "anyOf": [
        {
          "maxLength": 2048,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Organization website URL",
      "title": "Url"
    },
    "postal_code": {
      "anyOf": [
        {
          "maxLength": 255,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Postal/ZIP code",
      "title": "Postal Code"
    },
    "street_address": {
      "anyOf": [
        {
          "maxLength": 1024,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Street address",
      "title": "Street Address"
    },
    "locality": {
      "anyOf": [
        {
          "maxLength": 255,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "City/locality",
      "title": "Locality"
    },
    "region": {
      "anyOf": [
        {
          "maxLength": 255,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "State/region",
      "title": "Region"
    },
    "country": {
      "anyOf": [
        {
          "maxLength": 255,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Country",
      "title": "Country"
    }
  },
  "required": [
    "path",
    "organization_type"
  ],
  "title": "OrganizationCreate",
  "type": "object",
  "x-model-name": "OrganizationCreate"
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

  validate(data: any): OrganizationCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('OrganizationCreate', 'Expected an object');
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: path
    if (!('path' in data)) {
      errors.push('Missing required field: path');
    } else {
      if (typeof data.path !== 'string') {
        errors.push('Field path must be a string');
      }
    }

    // Required field: organization_type
    if (!('organization_type' in data)) {
      errors.push('Missing required field: organization_type');
    } else {
      // Reference field - basic object check
      if (typeof data.organization_type !== 'object') {
        errors.push('Field organization_type must be an object');
      }
    }

    // Optional field: user_id
    if ('user_id' in data && data.user_id !== undefined && data.user_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: number
    if ('number' in data && data.number !== undefined && data.number !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: email
    if ('email' in data && data.email !== undefined && data.email !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: telephone
    if ('telephone' in data && data.telephone !== undefined && data.telephone !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: fax_number
    if ('fax_number' in data && data.fax_number !== undefined && data.fax_number !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: url
    if ('url' in data && data.url !== undefined && data.url !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: postal_code
    if ('postal_code' in data && data.postal_code !== undefined && data.postal_code !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: street_address
    if ('street_address' in data && data.street_address !== undefined && data.street_address !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: locality
    if ('locality' in data && data.locality !== undefined && data.locality !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: region
    if ('region' in data && data.region !== undefined && data.region !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: country
    if ('country' in data && data.country !== undefined && data.country !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('OrganizationCreate', errors.join('; '));
    }

    return data as OrganizationCreate;
  }

  safeValidate(data: any): { success: true; data: OrganizationCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('OrganizationCreate', String(error)) };
    }
  }
}

/**
 * Validator for OrganizationGet
 */
export class OrganizationGetValidator extends BaseValidator<OrganizationGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "GitLabConfigGet": {
      "properties": {
        "settings": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "title": "Settings"
        },
        "url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Url"
        },
        "full_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path"
        },
        "directory": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Directory"
        },
        "registry": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Registry"
        },
        "parent": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Parent"
        },
        "group_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Group Id"
        },
        "parent_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Parent Id"
        },
        "namespace_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Namespace Id"
        },
        "namespace_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Namespace Path"
        },
        "web_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Web Url"
        },
        "visibility": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Visibility"
        },
        "last_synced_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Last Synced At"
        }
      },
      "title": "GitLabConfigGet",
      "type": "object"
    },
    "OrganizationPropertiesGet": {
      "additionalProperties": true,
      "properties": {
        "gitlab": {
          "anyOf": [
            {
              "$ref": "#/$defs/GitLabConfigGet"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "OrganizationPropertiesGet",
      "type": "object"
    },
    "OrganizationType": {
      "enum": [
        "user",
        "community",
        "organization"
      ],
      "title": "OrganizationType",
      "type": "string"
    }
  },
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
      "description": "Organization unique identifier",
      "title": "Id",
      "type": "string"
    },
    "path": {
      "description": "Hierarchical path",
      "title": "Path",
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
      "description": "Organization title",
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
      "description": "Organization description",
      "title": "Description"
    },
    "organization_type": {
      "$ref": "#/$defs/OrganizationType",
      "description": "Type of organization"
    },
    "user_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Associated user ID",
      "title": "User Id"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/OrganizationPropertiesGet"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Additional properties"
    },
    "number": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Organization number",
      "title": "Number"
    },
    "email": {
      "anyOf": [
        {
          "format": "email",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Contact email",
      "title": "Email"
    },
    "telephone": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Phone number",
      "title": "Telephone"
    },
    "fax_number": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Fax number",
      "title": "Fax Number"
    },
    "url": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Website URL",
      "title": "Url"
    },
    "postal_code": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Postal code",
      "title": "Postal Code"
    },
    "street_address": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Street address",
      "title": "Street Address"
    },
    "locality": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "City/locality",
      "title": "Locality"
    },
    "region": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "State/region",
      "title": "Region"
    },
    "country": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Country",
      "title": "Country"
    }
  },
  "required": [
    "id",
    "path",
    "organization_type"
  ],
  "title": "OrganizationGet",
  "type": "object",
  "x-model-name": "OrganizationGet"
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

  validate(data: any): OrganizationGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('OrganizationGet', 'Expected an object');
    }

    // Optional field: created_at
    if ('created_at' in data && data.created_at !== undefined && data.created_at !== null) {
      // Union type - skipping detailed validation
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

    // Required field: path
    if (!('path' in data)) {
      errors.push('Missing required field: path');
    } else {
      if (typeof data.path !== 'string') {
        errors.push('Field path must be a string');
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

    // Required field: organization_type
    if (!('organization_type' in data)) {
      errors.push('Missing required field: organization_type');
    } else {
      // Reference field - basic object check
      if (typeof data.organization_type !== 'object') {
        errors.push('Field organization_type must be an object');
      }
    }

    // Optional field: user_id
    if ('user_id' in data && data.user_id !== undefined && data.user_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: number
    if ('number' in data && data.number !== undefined && data.number !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: email
    if ('email' in data && data.email !== undefined && data.email !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: telephone
    if ('telephone' in data && data.telephone !== undefined && data.telephone !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: fax_number
    if ('fax_number' in data && data.fax_number !== undefined && data.fax_number !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: url
    if ('url' in data && data.url !== undefined && data.url !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: postal_code
    if ('postal_code' in data && data.postal_code !== undefined && data.postal_code !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: street_address
    if ('street_address' in data && data.street_address !== undefined && data.street_address !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: locality
    if ('locality' in data && data.locality !== undefined && data.locality !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: region
    if ('region' in data && data.region !== undefined && data.region !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: country
    if ('country' in data && data.country !== undefined && data.country !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('OrganizationGet', errors.join('; '));
    }

    return data as OrganizationGet;
  }

  safeValidate(data: any): { success: true; data: OrganizationGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('OrganizationGet', String(error)) };
    }
  }
}

/**
 * Validator for OrganizationList
 */
export class OrganizationListValidator extends BaseValidator<OrganizationList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "OrganizationType": {
      "enum": [
        "user",
        "community",
        "organization"
      ],
      "title": "OrganizationType",
      "type": "string"
    }
  },
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
      "description": "Organization unique identifier",
      "title": "Id",
      "type": "string"
    },
    "path": {
      "description": "Hierarchical path",
      "title": "Path",
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
      "description": "Organization title",
      "title": "Title"
    },
    "organization_type": {
      "$ref": "#/$defs/OrganizationType",
      "description": "Type of organization"
    },
    "user_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Associated user ID",
      "title": "User Id"
    },
    "email": {
      "anyOf": [
        {
          "format": "email",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Contact email",
      "title": "Email"
    }
  },
  "required": [
    "id",
    "path",
    "organization_type"
  ],
  "title": "OrganizationList",
  "type": "object",
  "x-model-name": "OrganizationList"
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

  validate(data: any): OrganizationList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('OrganizationList', 'Expected an object');
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

    // Required field: path
    if (!('path' in data)) {
      errors.push('Missing required field: path');
    } else {
      if (typeof data.path !== 'string') {
        errors.push('Field path must be a string');
      }
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: organization_type
    if (!('organization_type' in data)) {
      errors.push('Missing required field: organization_type');
    } else {
      // Reference field - basic object check
      if (typeof data.organization_type !== 'object') {
        errors.push('Field organization_type must be an object');
      }
    }

    // Optional field: user_id
    if ('user_id' in data && data.user_id !== undefined && data.user_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: email
    if ('email' in data && data.email !== undefined && data.email !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('OrganizationList', errors.join('; '));
    }

    return data as OrganizationList;
  }

  safeValidate(data: any): { success: true; data: OrganizationList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('OrganizationList', String(error)) };
    }
  }
}

/**
 * Validator for OrganizationUpdate
 */
export class OrganizationUpdateValidator extends BaseValidator<OrganizationUpdate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "GitLabConfig": {
      "properties": {
        "settings": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "title": "Settings"
        },
        "url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Url"
        },
        "full_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path"
        },
        "directory": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Directory"
        },
        "registry": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Registry"
        },
        "parent": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Parent"
        },
        "group_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Group Id"
        },
        "parent_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Parent Id"
        },
        "namespace_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Namespace Id"
        },
        "namespace_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Namespace Path"
        },
        "web_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Web Url"
        },
        "visibility": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Visibility"
        },
        "last_synced_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Last Synced At"
        },
        "token": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Token"
        }
      },
      "title": "GitLabConfig",
      "type": "object"
    },
    "OrganizationProperties": {
      "additionalProperties": true,
      "properties": {
        "gitlab": {
          "anyOf": [
            {
              "$ref": "#/$defs/GitLabConfig"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "OrganizationProperties",
      "type": "object"
    },
    "OrganizationType": {
      "enum": [
        "user",
        "community",
        "organization"
      ],
      "title": "OrganizationType",
      "type": "string"
    }
  },
  "properties": {
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
    "path": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Path"
    },
    "organization_type": {
      "anyOf": [
        {
          "$ref": "#/$defs/OrganizationType"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "user_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "User Id"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/OrganizationProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "number": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Number"
    },
    "email": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Email"
    },
    "telephone": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Telephone"
    },
    "fax_number": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Fax Number"
    },
    "url": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Url"
    },
    "postal_code": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Postal Code"
    },
    "street_address": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Street Address"
    },
    "locality": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Locality"
    },
    "region": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Region"
    },
    "country": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Country"
    }
  },
  "title": "OrganizationUpdate",
  "type": "object",
  "x-model-name": "OrganizationUpdate"
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

  validate(data: any): OrganizationUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('OrganizationUpdate', 'Expected an object');
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: path
    if ('path' in data && data.path !== undefined && data.path !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: organization_type
    if ('organization_type' in data && data.organization_type !== undefined && data.organization_type !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: user_id
    if ('user_id' in data && data.user_id !== undefined && data.user_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: number
    if ('number' in data && data.number !== undefined && data.number !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: email
    if ('email' in data && data.email !== undefined && data.email !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: telephone
    if ('telephone' in data && data.telephone !== undefined && data.telephone !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: fax_number
    if ('fax_number' in data && data.fax_number !== undefined && data.fax_number !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: url
    if ('url' in data && data.url !== undefined && data.url !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: postal_code
    if ('postal_code' in data && data.postal_code !== undefined && data.postal_code !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: street_address
    if ('street_address' in data && data.street_address !== undefined && data.street_address !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: locality
    if ('locality' in data && data.locality !== undefined && data.locality !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: region
    if ('region' in data && data.region !== undefined && data.region !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: country
    if ('country' in data && data.country !== undefined && data.country !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('OrganizationUpdate', errors.join('; '));
    }

    return data as OrganizationUpdate;
  }

  safeValidate(data: any): { success: true; data: OrganizationUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('OrganizationUpdate', String(error)) };
    }
  }
}

/**
 * Validator for OrganizationQuery
 */
export class OrganizationQueryValidator extends BaseValidator<OrganizationQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "GitLabConfig": {
      "properties": {
        "settings": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "title": "Settings"
        },
        "url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Url"
        },
        "full_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path"
        },
        "directory": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Directory"
        },
        "registry": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Registry"
        },
        "parent": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Parent"
        },
        "group_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Group Id"
        },
        "parent_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Parent Id"
        },
        "namespace_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Namespace Id"
        },
        "namespace_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Namespace Path"
        },
        "web_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Web Url"
        },
        "visibility": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Visibility"
        },
        "last_synced_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Last Synced At"
        },
        "token": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Token"
        }
      },
      "title": "GitLabConfig",
      "type": "object"
    },
    "OrganizationProperties": {
      "additionalProperties": true,
      "properties": {
        "gitlab": {
          "anyOf": [
            {
              "$ref": "#/$defs/GitLabConfig"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "OrganizationProperties",
      "type": "object"
    },
    "OrganizationType": {
      "enum": [
        "user",
        "community",
        "organization"
      ],
      "title": "OrganizationType",
      "type": "string"
    }
  },
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
    "path": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Path"
    },
    "organization_type": {
      "anyOf": [
        {
          "$ref": "#/$defs/OrganizationType"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "user_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "User Id"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/OrganizationProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "number": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Number"
    },
    "email": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Email"
    },
    "telephone": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Telephone"
    },
    "fax_number": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Fax Number"
    },
    "url": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Url"
    },
    "postal_code": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Postal Code"
    },
    "street_address": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Street Address"
    },
    "locality": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Locality"
    },
    "region": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Region"
    },
    "country": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Country"
    }
  },
  "title": "OrganizationQuery",
  "type": "object",
  "x-model-name": "OrganizationQuery"
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

  validate(data: any): OrganizationQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('OrganizationQuery', 'Expected an object');
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

    // Optional field: path
    if ('path' in data && data.path !== undefined && data.path !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: organization_type
    if ('organization_type' in data && data.organization_type !== undefined && data.organization_type !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: user_id
    if ('user_id' in data && data.user_id !== undefined && data.user_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: number
    if ('number' in data && data.number !== undefined && data.number !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: email
    if ('email' in data && data.email !== undefined && data.email !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: telephone
    if ('telephone' in data && data.telephone !== undefined && data.telephone !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: fax_number
    if ('fax_number' in data && data.fax_number !== undefined && data.fax_number !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: url
    if ('url' in data && data.url !== undefined && data.url !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: postal_code
    if ('postal_code' in data && data.postal_code !== undefined && data.postal_code !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: street_address
    if ('street_address' in data && data.street_address !== undefined && data.street_address !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: locality
    if ('locality' in data && data.locality !== undefined && data.locality !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: region
    if ('region' in data && data.region !== undefined && data.region !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: country
    if ('country' in data && data.country !== undefined && data.country !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('OrganizationQuery', errors.join('; '));
    }

    return data as OrganizationQuery;
  }

  safeValidate(data: any): { success: true; data: OrganizationQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('OrganizationQuery', String(error)) };
    }
  }
}

/**
 * Request to create an organization via Temporal workflow.
 */
export class OrganizationTaskRequestValidator extends BaseValidator<OrganizationTaskRequest> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "GitLabCredentials": {
      "description": "GitLab connection credentials.",
      "properties": {
        "gitlab_url": {
          "title": "Gitlab Url",
          "type": "string"
        },
        "gitlab_token": {
          "title": "Gitlab Token",
          "type": "string"
        }
      },
      "required": [
        "gitlab_url",
        "gitlab_token"
      ],
      "title": "GitLabCredentials",
      "type": "object"
    }
  },
  "description": "Request to create an organization via Temporal workflow.",
  "properties": {
    "organization": {
      "additionalProperties": true,
      "title": "Organization",
      "type": "object"
    },
    "gitlab": {
      "$ref": "#/$defs/GitLabCredentials"
    },
    "parent_group_id": {
      "title": "Parent Group Id",
      "type": "integer"
    }
  },
  "required": [
    "organization",
    "gitlab",
    "parent_group_id"
  ],
  "title": "OrganizationTaskRequest",
  "type": "object",
  "x-model-name": "OrganizationTaskRequest"
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

  validate(data: any): OrganizationTaskRequest {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('OrganizationTaskRequest', 'Expected an object');
    }

    // Required field: organization
    if (!('organization' in data)) {
      errors.push('Missing required field: organization');
    } else {
      if (typeof data.organization !== 'object' || data.organization === null) {
        errors.push('Field organization must be an object');
      }
    }

    // Required field: gitlab
    if (!('gitlab' in data)) {
      errors.push('Missing required field: gitlab');
    } else {
      // Reference field - basic object check
      if (typeof data.gitlab !== 'object') {
        errors.push('Field gitlab must be an object');
      }
    }

    // Required field: parent_group_id
    if (!('parent_group_id' in data)) {
      errors.push('Missing required field: parent_group_id');
    } else {
      if (typeof data.parent_group_id !== 'number') {
        errors.push('Field parent_group_id must be a number');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('OrganizationTaskRequest', errors.join('; '));
    }

    return data as OrganizationTaskRequest;
  }

  safeValidate(data: any): { success: true; data: OrganizationTaskRequest } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('OrganizationTaskRequest', String(error)) };
    }
  }
}

/**
 * Organization configuration.
 */
export class OrganizationConfigValidator extends BaseValidator<OrganizationConfig> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "GitHubConfig": {
      "description": "GitHub repository configuration (future support).",
      "properties": {
        "url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "GitHub instance URL",
          "title": "Url"
        },
        "token": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "GitHub API token",
          "title": "Token"
        },
        "organization": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "GitHub organization",
          "title": "Organization"
        }
      },
      "title": "GitHubConfig",
      "type": "object"
    },
    "GitLabConfig": {
      "description": "GitLab repository configuration.",
      "properties": {
        "url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "GitLab instance URL",
          "title": "Url"
        },
        "token": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "GitLab API token",
          "title": "Token"
        },
        "parent": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Parent group ID",
          "title": "Parent"
        },
        "full_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Full path in GitLab",
          "title": "Full Path"
        },
        "group_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "GitLab group ID",
          "title": "Group Id"
        },
        "parent_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Parent group ID",
          "title": "Parent Id"
        },
        "namespace_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Namespace ID",
          "title": "Namespace Id"
        },
        "namespace_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Namespace path",
          "title": "Namespace Path"
        },
        "web_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Web URL",
          "title": "Web Url"
        },
        "visibility": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Visibility level",
          "title": "Visibility"
        },
        "last_synced_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Last sync timestamp",
          "title": "Last Synced At"
        }
      },
      "title": "GitLabConfig",
      "type": "object"
    }
  },
  "description": "Organization configuration.",
  "properties": {
    "name": {
      "description": "Organization display name",
      "title": "Name",
      "type": "string"
    },
    "path": {
      "description": "Organization path/slug",
      "title": "Path",
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
      "description": "Organization description",
      "title": "Description"
    },
    "settings": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "description": "Organization-specific settings",
      "title": "Settings"
    },
    "gitlab": {
      "anyOf": [
        {
          "$ref": "#/$defs/GitLabConfig"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "GitLab configuration"
    },
    "github": {
      "anyOf": [
        {
          "$ref": "#/$defs/GitHubConfig"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "GitHub configuration (future)"
    }
  },
  "required": [
    "name",
    "path"
  ],
  "title": "OrganizationConfig",
  "type": "object",
  "x-model-name": "OrganizationConfig"
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

  validate(data: any): OrganizationConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('OrganizationConfig', 'Expected an object');
    }

    // Required field: name
    if (!('name' in data)) {
      errors.push('Missing required field: name');
    } else {
      if (typeof data.name !== 'string') {
        errors.push('Field name must be a string');
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

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: settings
    if ('settings' in data && data.settings !== undefined && data.settings !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: gitlab
    if ('gitlab' in data && data.gitlab !== undefined && data.gitlab !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: github
    if ('github' in data && data.github !== undefined && data.github !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('OrganizationConfig', errors.join('; '));
    }

    return data as OrganizationConfig;
  }

  safeValidate(data: any): { success: true; data: OrganizationConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('OrganizationConfig', String(error)) };
    }
  }
}

/**
 * Organization configuration with nested course families.
 */
export class HierarchicalOrganizationConfigValidator extends BaseValidator<HierarchicalOrganizationConfig> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseContentConfig": {
      "description": "Configuration for course content (assignments, units, etc.).",
      "properties": {
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
          "description": "Title of the course content (defaults from example if submittable)",
          "title": "Title"
        },
        "path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Hierarchical path using dots (optional; generated when omitted)",
          "title": "Path"
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
          "description": "Description of the content",
          "title": "Description"
        },
        "content_type": {
          "description": "Slug of the course content type (must match a defined content_type)",
          "title": "Content Type",
          "type": "string"
        },
        "position": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Position for ordering (defaults to auto-increment)",
          "title": "Position"
        },
        "max_group_size": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Maximum group size for submissions",
          "title": "Max Group Size"
        },
        "max_test_runs": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Maximum test runs allowed",
          "title": "Max Test Runs"
        },
        "max_submissions": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Maximum submissions allowed",
          "title": "Max Submissions"
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
          "description": "Example identifier (e.g., 'week1.fibonacci') - required for submittable content",
          "title": "Example Identifier"
        },
        "example_version_tag": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Version tag of the example (e.g., 'v1.0', 'latest') - defaults to latest",
          "title": "Example Version Tag"
        },
        "execution_backend": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Override execution backend slug for this content",
          "title": "Execution Backend"
        },
        "contents": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/CourseContentConfig"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "description": "Nested course contents (for units containing assignments)",
          "title": "Contents"
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
          "description": "Additional properties for the content",
          "title": "Properties"
        }
      },
      "required": [
        "content_type"
      ],
      "title": "CourseContentConfig",
      "type": "object"
    },
    "CourseContentTypeConfig": {
      "description": "Course content type configuration for deployment.",
      "properties": {
        "slug": {
          "description": "Unique identifier for the content type",
          "title": "Slug",
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
          "description": "Display title for the content type",
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
          "description": "Description of the content type",
          "title": "Description"
        },
        "color": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": "green",
          "description": "Display color (hex, rgb, hsl, or named color)",
          "title": "Color"
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
          "description": "Additional properties",
          "title": "Properties"
        },
        "kind": {
          "description": "ID of the course content kind (e.g., 'assignment', 'unit')",
          "title": "Kind",
          "type": "string"
        }
      },
      "required": [
        "slug",
        "kind"
      ],
      "title": "CourseContentTypeConfig",
      "type": "object"
    },
    "CourseProjects": {
      "description": "Configuration for course-related GitLab projects.",
      "properties": {
        "tests": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": "tests",
          "description": "Path for tests project",
          "title": "Tests"
        },
        "student_template": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": "student-template",
          "description": "Path for student template project",
          "title": "Student Template"
        },
        "reference": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": "reference",
          "description": "Path for reference solution project",
          "title": "Reference"
        },
        "examples": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": "examples",
          "description": "Path for examples project",
          "title": "Examples"
        },
        "documents": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": "documents",
          "description": "Path for documents project",
          "title": "Documents"
        }
      },
      "title": "CourseProjects",
      "type": "object"
    },
    "ExecutionBackendReference": {
      "description": "Reference to an execution backend by slug for linking to courses.",
      "properties": {
        "slug": {
          "description": "Slug of the execution backend to link",
          "title": "Slug",
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
          "description": "Course-specific overrides for this backend (optional)",
          "title": "Properties"
        }
      },
      "required": [
        "slug"
      ],
      "title": "ExecutionBackendReference",
      "type": "object"
    },
    "GitHubConfig": {
      "description": "GitHub repository configuration (future support).",
      "properties": {
        "url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "GitHub instance URL",
          "title": "Url"
        },
        "token": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "GitHub API token",
          "title": "Token"
        },
        "organization": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "GitHub organization",
          "title": "Organization"
        }
      },
      "title": "GitHubConfig",
      "type": "object"
    },
    "GitLabConfig": {
      "description": "GitLab repository configuration.",
      "properties": {
        "url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "GitLab instance URL",
          "title": "Url"
        },
        "token": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "GitLab API token",
          "title": "Token"
        },
        "parent": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Parent group ID",
          "title": "Parent"
        },
        "full_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Full path in GitLab",
          "title": "Full Path"
        },
        "group_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "GitLab group ID",
          "title": "Group Id"
        },
        "parent_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Parent group ID",
          "title": "Parent Id"
        },
        "namespace_id": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Namespace ID",
          "title": "Namespace Id"
        },
        "namespace_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Namespace path",
          "title": "Namespace Path"
        },
        "web_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Web URL",
          "title": "Web Url"
        },
        "visibility": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Visibility level",
          "title": "Visibility"
        },
        "last_synced_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Last sync timestamp",
          "title": "Last Synced At"
        }
      },
      "title": "GitLabConfig",
      "type": "object"
    },
    "HierarchicalCourseConfig": {
      "description": "Course configuration for hierarchical deployment.",
      "properties": {
        "name": {
          "description": "Course display name",
          "title": "Name",
          "type": "string"
        },
        "path": {
          "description": "Course path/slug",
          "title": "Path",
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
          "description": "Course description",
          "title": "Description"
        },
        "projects": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseProjects"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Course project structure"
        },
        "execution_backends": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/ExecutionBackendReference"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "References to execution backends to link to this course (by slug)",
          "title": "Execution Backends"
        },
        "content_types": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/CourseContentTypeConfig"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "description": "Course content types to be created (assignments, units, etc.)",
          "title": "Content Types"
        },
        "contents": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/CourseContentConfig"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "description": "Course contents hierarchy (assignments, units, etc.)",
          "title": "Contents"
        },
        "settings": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "description": "Course-specific settings",
          "title": "Settings"
        }
      },
      "required": [
        "name",
        "path"
      ],
      "title": "HierarchicalCourseConfig",
      "type": "object"
    },
    "HierarchicalCourseFamilyConfig": {
      "description": "Course family configuration with nested courses.",
      "properties": {
        "name": {
          "description": "Course family display name",
          "title": "Name",
          "type": "string"
        },
        "path": {
          "description": "Course family path/slug",
          "title": "Path",
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
          "description": "Course family description",
          "title": "Description"
        },
        "settings": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "description": "Course family-specific settings",
          "title": "Settings"
        },
        "courses": {
          "description": "List of courses in this course family",
          "items": {
            "$ref": "#/$defs/HierarchicalCourseConfig"
          },
          "title": "Courses",
          "type": "array"
        }
      },
      "required": [
        "name",
        "path"
      ],
      "title": "HierarchicalCourseFamilyConfig",
      "type": "object"
    }
  },
  "description": "Organization configuration with nested course families.",
  "properties": {
    "name": {
      "description": "Organization display name",
      "title": "Name",
      "type": "string"
    },
    "path": {
      "description": "Organization path/slug",
      "title": "Path",
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
      "description": "Organization description",
      "title": "Description"
    },
    "settings": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "description": "Organization-specific settings",
      "title": "Settings"
    },
    "gitlab": {
      "anyOf": [
        {
          "$ref": "#/$defs/GitLabConfig"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "GitLab configuration"
    },
    "github": {
      "anyOf": [
        {
          "$ref": "#/$defs/GitHubConfig"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "GitHub configuration (future)"
    },
    "course_families": {
      "description": "List of course families in this organization",
      "items": {
        "$ref": "#/$defs/HierarchicalCourseFamilyConfig"
      },
      "title": "Course Families",
      "type": "array"
    }
  },
  "required": [
    "name",
    "path"
  ],
  "title": "HierarchicalOrganizationConfig",
  "type": "object",
  "x-model-name": "HierarchicalOrganizationConfig"
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

  validate(data: any): HierarchicalOrganizationConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('HierarchicalOrganizationConfig', 'Expected an object');
    }

    // Required field: name
    if (!('name' in data)) {
      errors.push('Missing required field: name');
    } else {
      if (typeof data.name !== 'string') {
        errors.push('Field name must be a string');
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

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: settings
    if ('settings' in data && data.settings !== undefined && data.settings !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: gitlab
    if ('gitlab' in data && data.gitlab !== undefined && data.gitlab !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: github
    if ('github' in data && data.github !== undefined && data.github !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_families
    if ('course_families' in data && data.course_families !== undefined && data.course_families !== null) {
      if (!Array.isArray(data.course_families)) {
        errors.push('Field course_families must be an array');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('HierarchicalOrganizationConfig', errors.join('; '));
    }

    return data as HierarchicalOrganizationConfig;
  }

  safeValidate(data: any): { success: true; data: HierarchicalOrganizationConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('HierarchicalOrganizationConfig', String(error)) };
    }
  }
}
