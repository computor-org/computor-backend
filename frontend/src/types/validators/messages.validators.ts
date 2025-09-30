/**
 * Auto-generated validation classes for Messages models
 * DO NOT EDIT MANUALLY
 */

import type { MessageCreate, MessageGet, MessageList, MessageQuery, MessageUpdate } from '../generated/messages';
import { BaseValidator, ValidationError } from './BaseValidator';

/**
 * Validator for MessageCreate
 */
export class MessageCreateValidator extends BaseValidator<MessageCreate> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "properties": {
    "parent_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Parent Id"
    },
    "level": {
      "default": 0,
      "title": "Level",
      "type": "integer"
    },
    "title": {
      "title": "Title",
      "type": "string"
    },
    "content": {
      "title": "Content",
      "type": "string"
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
    "course_member_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Member Id"
    },
    "submission_group_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Submission Group Id"
    },
    "course_group_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Group Id"
    },
    "course_content_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Content Id"
    },
    "course_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Id"
    }
  },
  "required": [
    "title",
    "content"
  ],
  "title": "MessageCreate",
  "type": "object",
  "x-model-name": "MessageCreate"
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

  validate(data: any): MessageCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('MessageCreate', 'Expected an object');
    }

    // Optional field: parent_id
    if ('parent_id' in data && data.parent_id !== undefined && data.parent_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: level
    if ('level' in data && data.level !== undefined && data.level !== null) {
      if (typeof data.level !== 'number') {
        errors.push('Field level must be a number');
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

    // Required field: content
    if (!('content' in data)) {
      errors.push('Missing required field: content');
    } else {
      if (typeof data.content !== 'string') {
        errors.push('Field content must be a string');
      }
    }

    // Optional field: user_id
    if ('user_id' in data && data.user_id !== undefined && data.user_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_member_id
    if ('course_member_id' in data && data.course_member_id !== undefined && data.course_member_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: submission_group_id
    if ('submission_group_id' in data && data.submission_group_id !== undefined && data.submission_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_group_id
    if ('course_group_id' in data && data.course_group_id !== undefined && data.course_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_content_id
    if ('course_content_id' in data && data.course_content_id !== undefined && data.course_content_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_id
    if ('course_id' in data && data.course_id !== undefined && data.course_id !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('MessageCreate', errors.join('; '));
    }

    return data as MessageCreate;
  }

  safeValidate(data: any): { success: true; data: MessageCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('MessageCreate', String(error)) };
    }
  }
}

/**
 * Validator for MessageUpdate
 */
export class MessageUpdateValidator extends BaseValidator<MessageUpdate> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
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
    "content": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Content"
    }
  },
  "title": "MessageUpdate",
  "type": "object",
  "x-model-name": "MessageUpdate"
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

  validate(data: any): MessageUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('MessageUpdate', 'Expected an object');
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: content
    if ('content' in data && data.content !== undefined && data.content !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('MessageUpdate', errors.join('; '));
    }

    return data as MessageUpdate;
  }

  safeValidate(data: any): { success: true; data: MessageUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('MessageUpdate', String(error)) };
    }
  }
}

/**
 * Validator for MessageGet
 */
export class MessageGetValidator extends BaseValidator<MessageGet> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "$defs": {
    "MessageAuthor": {
      "properties": {
        "given_name": {
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
          "description": "Author's given name",
          "title": "Given Name"
        },
        "family_name": {
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
          "description": "Author's family name",
          "title": "Family Name"
        }
      },
      "title": "MessageAuthor",
      "type": "object"
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
      "title": "Id",
      "type": "string"
    },
    "title": {
      "title": "Title",
      "type": "string"
    },
    "content": {
      "title": "Content",
      "type": "string"
    },
    "level": {
      "title": "Level",
      "type": "integer"
    },
    "parent_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Parent Id"
    },
    "author_id": {
      "title": "Author Id",
      "type": "string"
    },
    "author": {
      "anyOf": [
        {
          "$ref": "#/$defs/MessageAuthor"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Author details"
    },
    "is_read": {
      "default": false,
      "title": "Is Read",
      "type": "boolean"
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
    "course_member_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Member Id"
    },
    "submission_group_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Submission Group Id"
    },
    "course_group_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Group Id"
    },
    "course_content_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Content Id"
    },
    "course_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Id"
    }
  },
  "required": [
    "id",
    "title",
    "content",
    "level",
    "author_id"
  ],
  "title": "MessageGet",
  "type": "object",
  "x-model-name": "MessageGet"
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

  validate(data: any): MessageGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('MessageGet', 'Expected an object');
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

    // Required field: title
    if (!('title' in data)) {
      errors.push('Missing required field: title');
    } else {
      if (typeof data.title !== 'string') {
        errors.push('Field title must be a string');
      }
    }

    // Required field: content
    if (!('content' in data)) {
      errors.push('Missing required field: content');
    } else {
      if (typeof data.content !== 'string') {
        errors.push('Field content must be a string');
      }
    }

    // Required field: level
    if (!('level' in data)) {
      errors.push('Missing required field: level');
    } else {
      if (typeof data.level !== 'number') {
        errors.push('Field level must be a number');
      }
    }

    // Optional field: parent_id
    if ('parent_id' in data && data.parent_id !== undefined && data.parent_id !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: author_id
    if (!('author_id' in data)) {
      errors.push('Missing required field: author_id');
    } else {
      if (typeof data.author_id !== 'string') {
        errors.push('Field author_id must be a string');
      }
    }

    // Optional field: author
    if ('author' in data && data.author !== undefined && data.author !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: is_read
    if ('is_read' in data && data.is_read !== undefined && data.is_read !== null) {
      if (typeof data.is_read !== 'boolean') {
        errors.push('Field is_read must be a boolean');
      }
    }

    // Optional field: user_id
    if ('user_id' in data && data.user_id !== undefined && data.user_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_member_id
    if ('course_member_id' in data && data.course_member_id !== undefined && data.course_member_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: submission_group_id
    if ('submission_group_id' in data && data.submission_group_id !== undefined && data.submission_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_group_id
    if ('course_group_id' in data && data.course_group_id !== undefined && data.course_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_content_id
    if ('course_content_id' in data && data.course_content_id !== undefined && data.course_content_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_id
    if ('course_id' in data && data.course_id !== undefined && data.course_id !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('MessageGet', errors.join('; '));
    }

    return data as MessageGet;
  }

  safeValidate(data: any): { success: true; data: MessageGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('MessageGet', String(error)) };
    }
  }
}

/**
 * Validator for MessageList
 */
export class MessageListValidator extends BaseValidator<MessageList> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "$defs": {
    "MessageAuthor": {
      "properties": {
        "given_name": {
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
          "description": "Author's given name",
          "title": "Given Name"
        },
        "family_name": {
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
          "description": "Author's family name",
          "title": "Family Name"
        }
      },
      "title": "MessageAuthor",
      "type": "object"
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
      "title": "Id",
      "type": "string"
    },
    "title": {
      "title": "Title",
      "type": "string"
    },
    "content": {
      "title": "Content",
      "type": "string"
    },
    "level": {
      "title": "Level",
      "type": "integer"
    },
    "parent_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Parent Id"
    },
    "author_id": {
      "title": "Author Id",
      "type": "string"
    },
    "author": {
      "anyOf": [
        {
          "$ref": "#/$defs/MessageAuthor"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Author details"
    },
    "is_read": {
      "default": false,
      "title": "Is Read",
      "type": "boolean"
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
    "course_member_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Member Id"
    },
    "submission_group_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Submission Group Id"
    },
    "course_group_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Group Id"
    },
    "course_content_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Content Id"
    },
    "course_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Id"
    }
  },
  "required": [
    "id",
    "title",
    "content",
    "level",
    "author_id"
  ],
  "title": "MessageList",
  "type": "object",
  "x-model-name": "MessageList"
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

  validate(data: any): MessageList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('MessageList', 'Expected an object');
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

    // Required field: title
    if (!('title' in data)) {
      errors.push('Missing required field: title');
    } else {
      if (typeof data.title !== 'string') {
        errors.push('Field title must be a string');
      }
    }

    // Required field: content
    if (!('content' in data)) {
      errors.push('Missing required field: content');
    } else {
      if (typeof data.content !== 'string') {
        errors.push('Field content must be a string');
      }
    }

    // Required field: level
    if (!('level' in data)) {
      errors.push('Missing required field: level');
    } else {
      if (typeof data.level !== 'number') {
        errors.push('Field level must be a number');
      }
    }

    // Optional field: parent_id
    if ('parent_id' in data && data.parent_id !== undefined && data.parent_id !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: author_id
    if (!('author_id' in data)) {
      errors.push('Missing required field: author_id');
    } else {
      if (typeof data.author_id !== 'string') {
        errors.push('Field author_id must be a string');
      }
    }

    // Optional field: author
    if ('author' in data && data.author !== undefined && data.author !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: is_read
    if ('is_read' in data && data.is_read !== undefined && data.is_read !== null) {
      if (typeof data.is_read !== 'boolean') {
        errors.push('Field is_read must be a boolean');
      }
    }

    // Optional field: user_id
    if ('user_id' in data && data.user_id !== undefined && data.user_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_member_id
    if ('course_member_id' in data && data.course_member_id !== undefined && data.course_member_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: submission_group_id
    if ('submission_group_id' in data && data.submission_group_id !== undefined && data.submission_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_group_id
    if ('course_group_id' in data && data.course_group_id !== undefined && data.course_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_content_id
    if ('course_content_id' in data && data.course_content_id !== undefined && data.course_content_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_id
    if ('course_id' in data && data.course_id !== undefined && data.course_id !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('MessageList', errors.join('; '));
    }

    return data as MessageList;
  }

  safeValidate(data: any): { success: true; data: MessageList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('MessageList', String(error)) };
    }
  }
}

/**
 * Validator for MessageQuery
 */
export class MessageQueryValidator extends BaseValidator<MessageQuery> {
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
      "title": "Id"
    },
    "parent_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Parent Id"
    },
    "author_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Author Id"
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
    "course_member_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Member Id"
    },
    "submission_group_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Submission Group Id"
    },
    "course_group_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Group Id"
    },
    "course_content_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Content Id"
    },
    "course_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Id"
    }
  },
  "title": "MessageQuery",
  "type": "object",
  "x-model-name": "MessageQuery"
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

  validate(data: any): MessageQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('MessageQuery', 'Expected an object');
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

    // Optional field: parent_id
    if ('parent_id' in data && data.parent_id !== undefined && data.parent_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: author_id
    if ('author_id' in data && data.author_id !== undefined && data.author_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: user_id
    if ('user_id' in data && data.user_id !== undefined && data.user_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_member_id
    if ('course_member_id' in data && data.course_member_id !== undefined && data.course_member_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: submission_group_id
    if ('submission_group_id' in data && data.submission_group_id !== undefined && data.submission_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_group_id
    if ('course_group_id' in data && data.course_group_id !== undefined && data.course_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_content_id
    if ('course_content_id' in data && data.course_content_id !== undefined && data.course_content_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_id
    if ('course_id' in data && data.course_id !== undefined && data.course_id !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('MessageQuery', errors.join('; '));
    }

    return data as MessageQuery;
  }

  safeValidate(data: any): { success: true; data: MessageQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('MessageQuery', String(error)) };
    }
  }
}
