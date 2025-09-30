/**
 * Auto-generated validation classes for Courses models
 * DO NOT EDIT MANUALLY
 */

import type { CodeAbilityCourseMeta, CourseConfig, CourseContentConfig, CourseContentCreate, CourseContentFileQuery, CourseContentGet, CourseContentKindCreate, CourseContentKindGet, CourseContentKindList, CourseContentKindQuery, CourseContentKindUpdate, CourseContentLecturerGet, CourseContentLecturerList, CourseContentLecturerQuery, CourseContentList, CourseContentProperties, CourseContentPropertiesGet, CourseContentQuery, CourseContentRepositoryLecturerGet, CourseContentStudentGet, CourseContentStudentList, CourseContentStudentProperties, CourseContentStudentQuery, CourseContentStudentUpdate, CourseContentTypeConfig, CourseContentTypeCreate, CourseContentTypeGet, CourseContentTypeList, CourseContentTypeQuery, CourseContentTypeUpdate, CourseContentUpdate, CourseCreate, CourseExecutionBackendConfig, CourseExecutionBackendCreate, CourseExecutionBackendGet, CourseExecutionBackendList, CourseExecutionBackendQuery, CourseExecutionBackendUpdate, CourseFamilyConfig, CourseFamilyCreate, CourseFamilyGet, CourseFamilyList, CourseFamilyProperties, CourseFamilyPropertiesGet, CourseFamilyQuery, CourseFamilyTaskRequest, CourseFamilyUpdate, CourseGet, CourseGroupConfig, CourseGroupCreate, CourseGroupGet, CourseGroupList, CourseGroupQuery, CourseGroupUpdate, CourseList, CourseMemberCommentCreate, CourseMemberCommentGet, CourseMemberCommentList, CourseMemberCommentQuery, CourseMemberCommentUpdate, CourseMemberCreate, CourseMemberGet, CourseMemberList, CourseMemberProperties, CourseMemberQuery, CourseMemberReadinessStatus, CourseMemberUpdate, CourseMemberValidationRequest, CourseProjects, CourseProjectsConfig, CourseProperties, CoursePropertiesGet, CourseQuery, CourseReleaseUpdate, CourseRoleGet, CourseRoleList, CourseRoleQuery, CourseSettingsConfig, CourseSignupResponse, CourseStudentGet, CourseStudentList, CourseStudentQuery, CourseStudentRepository, CourseTaskRequest, CourseTutorGet, CourseTutorList, CourseTutorQuery, CourseTutorRepository, CourseUpdate, GradedByCourseMember, HierarchicalCourseConfig, HierarchicalCourseFamilyConfig, ReleaseCourseContentCreate, ReleaseCourseCreate, TutorCourseMemberCourseContent, TutorCourseMemberGet, TutorCourseMemberList } from '../generated/courses';
import { BaseValidator, ValidationError } from './BaseValidator';

/**
 * Validator for TutorCourseMemberCourseContent
 */
export class TutorCourseMemberCourseContentValidator extends BaseValidator<TutorCourseMemberCourseContent> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "id": {
      "title": "Id",
      "type": "string"
    },
    "path": {
      "title": "Path",
      "type": "string"
    }
  },
  "required": [
    "id",
    "path"
  ],
  "title": "TutorCourseMemberCourseContent",
  "type": "object",
  "x-model-name": "TutorCourseMemberCourseContent"
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

  validate(data: any): TutorCourseMemberCourseContent {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('TutorCourseMemberCourseContent', 'Expected an object');
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

    if (errors.length > 0) {
      throw new ValidationError('TutorCourseMemberCourseContent', errors.join('; '));
    }

    return data as TutorCourseMemberCourseContent;
  }

  safeValidate(data: any): { success: true; data: TutorCourseMemberCourseContent } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('TutorCourseMemberCourseContent', String(error)) };
    }
  }
}

/**
 * Validator for TutorCourseMemberGet
 */
export class TutorCourseMemberGetValidator extends BaseValidator<TutorCourseMemberGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseMemberGitLabConfig": {
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
        "full_path_submission": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path Submission"
        }
      },
      "title": "CourseMemberGitLabConfig",
      "type": "object"
    },
    "CourseMemberProperties": {
      "additionalProperties": true,
      "properties": {
        "gitlab": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseMemberGitLabConfig"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "CourseMemberProperties",
      "type": "object"
    },
    "TutorCourseMemberCourseContent": {
      "properties": {
        "id": {
          "title": "Id",
          "type": "string"
        },
        "path": {
          "title": "Path",
          "type": "string"
        }
      },
      "required": [
        "id",
        "path"
      ],
      "title": "TutorCourseMemberCourseContent",
      "type": "object"
    },
    "UserList": {
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
          "description": "User unique identifier",
          "title": "Id",
          "type": "string"
        },
        "given_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "User's given name",
          "title": "Given Name"
        },
        "family_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "User's family name",
          "title": "Family Name"
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
          "description": "User's email address",
          "title": "Email"
        },
        "user_type": {
          "anyOf": [
            {
              "$ref": "#/$defs/UserTypeEnum"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Type of user account"
        },
        "username": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Unique username",
          "title": "Username"
        },
        "archived_at": {
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
          "description": "Archive timestamp",
          "title": "Archived At"
        }
      },
      "required": [
        "id"
      ],
      "title": "UserList",
      "type": "object"
    },
    "UserTypeEnum": {
      "enum": [
        "user",
        "token"
      ],
      "title": "UserTypeEnum",
      "type": "string"
    }
  },
  "properties": {
    "id": {
      "title": "Id",
      "type": "string"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseMemberProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "user_id": {
      "title": "User Id",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
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
    "course_role_id": {
      "title": "Course Role Id",
      "type": "string"
    },
    "unreviewed_course_contents": {
      "default": [],
      "items": {
        "$ref": "#/$defs/TutorCourseMemberCourseContent"
      },
      "title": "Unreviewed Course Contents",
      "type": "array"
    },
    "user": {
      "$ref": "#/$defs/UserList"
    }
  },
  "required": [
    "id",
    "user_id",
    "course_id",
    "course_role_id",
    "user"
  ],
  "title": "TutorCourseMemberGet",
  "type": "object",
  "x-model-name": "TutorCourseMemberGet"
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

  validate(data: any): TutorCourseMemberGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('TutorCourseMemberGet', 'Expected an object');
    }

    // Required field: id
    if (!('id' in data)) {
      errors.push('Missing required field: id');
    } else {
      if (typeof data.id !== 'string') {
        errors.push('Field id must be a string');
      }
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: user_id
    if (!('user_id' in data)) {
      errors.push('Missing required field: user_id');
    } else {
      if (typeof data.user_id !== 'string') {
        errors.push('Field user_id must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Optional field: course_group_id
    if ('course_group_id' in data && data.course_group_id !== undefined && data.course_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: course_role_id
    if (!('course_role_id' in data)) {
      errors.push('Missing required field: course_role_id');
    } else {
      if (typeof data.course_role_id !== 'string') {
        errors.push('Field course_role_id must be a string');
      }
    }

    // Optional field: unreviewed_course_contents
    if ('unreviewed_course_contents' in data && data.unreviewed_course_contents !== undefined && data.unreviewed_course_contents !== null) {
      if (!Array.isArray(data.unreviewed_course_contents)) {
        errors.push('Field unreviewed_course_contents must be an array');
      }
    }

    // Required field: user
    if (!('user' in data)) {
      errors.push('Missing required field: user');
    } else {
      // Reference field - basic object check
      if (typeof data.user !== 'object') {
        errors.push('Field user must be an object');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('TutorCourseMemberGet', errors.join('; '));
    }

    return data as TutorCourseMemberGet;
  }

  safeValidate(data: any): { success: true; data: TutorCourseMemberGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('TutorCourseMemberGet', String(error)) };
    }
  }
}

/**
 * Validator for TutorCourseMemberList
 */
export class TutorCourseMemberListValidator extends BaseValidator<TutorCourseMemberList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "UserList": {
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
          "description": "User unique identifier",
          "title": "Id",
          "type": "string"
        },
        "given_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "User's given name",
          "title": "Given Name"
        },
        "family_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "User's family name",
          "title": "Family Name"
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
          "description": "User's email address",
          "title": "Email"
        },
        "user_type": {
          "anyOf": [
            {
              "$ref": "#/$defs/UserTypeEnum"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Type of user account"
        },
        "username": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Unique username",
          "title": "Username"
        },
        "archived_at": {
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
          "description": "Archive timestamp",
          "title": "Archived At"
        }
      },
      "required": [
        "id"
      ],
      "title": "UserList",
      "type": "object"
    },
    "UserTypeEnum": {
      "enum": [
        "user",
        "token"
      ],
      "title": "UserTypeEnum",
      "type": "string"
    }
  },
  "properties": {
    "id": {
      "title": "Id",
      "type": "string"
    },
    "user_id": {
      "title": "User Id",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
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
    "course_role_id": {
      "title": "Course Role Id",
      "type": "string"
    },
    "unreviewed": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Unreviewed"
    },
    "user": {
      "$ref": "#/$defs/UserList"
    }
  },
  "required": [
    "id",
    "user_id",
    "course_id",
    "course_role_id",
    "user"
  ],
  "title": "TutorCourseMemberList",
  "type": "object",
  "x-model-name": "TutorCourseMemberList"
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

  validate(data: any): TutorCourseMemberList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('TutorCourseMemberList', 'Expected an object');
    }

    // Required field: id
    if (!('id' in data)) {
      errors.push('Missing required field: id');
    } else {
      if (typeof data.id !== 'string') {
        errors.push('Field id must be a string');
      }
    }

    // Required field: user_id
    if (!('user_id' in data)) {
      errors.push('Missing required field: user_id');
    } else {
      if (typeof data.user_id !== 'string') {
        errors.push('Field user_id must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Optional field: course_group_id
    if ('course_group_id' in data && data.course_group_id !== undefined && data.course_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: course_role_id
    if (!('course_role_id' in data)) {
      errors.push('Missing required field: course_role_id');
    } else {
      if (typeof data.course_role_id !== 'string') {
        errors.push('Field course_role_id must be a string');
      }
    }

    // Optional field: unreviewed
    if ('unreviewed' in data && data.unreviewed !== undefined && data.unreviewed !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: user
    if (!('user' in data)) {
      errors.push('Missing required field: user');
    } else {
      // Reference field - basic object check
      if (typeof data.user !== 'object') {
        errors.push('Field user must be an object');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('TutorCourseMemberList', errors.join('; '));
    }

    return data as TutorCourseMemberList;
  }

  safeValidate(data: any): { success: true; data: TutorCourseMemberList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('TutorCourseMemberList', String(error)) };
    }
  }
}

/**
 * Readiness state for a course member to start working on provider-backed tasks.
 */
export class CourseMemberReadinessStatusValidator extends BaseValidator<CourseMemberReadinessStatus> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Readiness state for a course member to start working on provider-backed tasks.",
  "properties": {
    "course_member_id": {
      "title": "Course Member Id",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
    },
    "organization_id": {
      "title": "Organization Id",
      "type": "string"
    },
    "course_role_id": {
      "title": "Course Role Id",
      "type": "string"
    },
    "provider_type": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Provider Type"
    },
    "provider": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Provider"
    },
    "requires_account": {
      "title": "Requires Account",
      "type": "boolean"
    },
    "has_account": {
      "title": "Has Account",
      "type": "boolean"
    },
    "is_ready": {
      "title": "Is Ready",
      "type": "boolean"
    },
    "provider_account_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Provider Account Id"
    },
    "provider_access_token": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Provider Access Token"
    }
  },
  "required": [
    "course_member_id",
    "course_id",
    "organization_id",
    "course_role_id",
    "requires_account",
    "has_account",
    "is_ready"
  ],
  "title": "CourseMemberReadinessStatus",
  "type": "object",
  "x-model-name": "CourseMemberReadinessStatus"
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

  validate(data: any): CourseMemberReadinessStatus {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseMemberReadinessStatus', 'Expected an object');
    }

    // Required field: course_member_id
    if (!('course_member_id' in data)) {
      errors.push('Missing required field: course_member_id');
    } else {
      if (typeof data.course_member_id !== 'string') {
        errors.push('Field course_member_id must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Required field: organization_id
    if (!('organization_id' in data)) {
      errors.push('Missing required field: organization_id');
    } else {
      if (typeof data.organization_id !== 'string') {
        errors.push('Field organization_id must be a string');
      }
    }

    // Required field: course_role_id
    if (!('course_role_id' in data)) {
      errors.push('Missing required field: course_role_id');
    } else {
      if (typeof data.course_role_id !== 'string') {
        errors.push('Field course_role_id must be a string');
      }
    }

    // Optional field: provider_type
    if ('provider_type' in data && data.provider_type !== undefined && data.provider_type !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: provider
    if ('provider' in data && data.provider !== undefined && data.provider !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: requires_account
    if (!('requires_account' in data)) {
      errors.push('Missing required field: requires_account');
    } else {
      if (typeof data.requires_account !== 'boolean') {
        errors.push('Field requires_account must be a boolean');
      }
    }

    // Required field: has_account
    if (!('has_account' in data)) {
      errors.push('Missing required field: has_account');
    } else {
      if (typeof data.has_account !== 'boolean') {
        errors.push('Field has_account must be a boolean');
      }
    }

    // Required field: is_ready
    if (!('is_ready' in data)) {
      errors.push('Missing required field: is_ready');
    } else {
      if (typeof data.is_ready !== 'boolean') {
        errors.push('Field is_ready must be a boolean');
      }
    }

    // Optional field: provider_account_id
    if ('provider_account_id' in data && data.provider_account_id !== undefined && data.provider_account_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: provider_access_token
    if ('provider_access_token' in data && data.provider_access_token !== undefined && data.provider_access_token !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseMemberReadinessStatus', errors.join('; '));
    }

    return data as CourseMemberReadinessStatus;
  }

  safeValidate(data: any): { success: true; data: CourseMemberReadinessStatus } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseMemberReadinessStatus', String(error)) };
    }
  }
}

/**
 * Validation parameters supplied when checking provider readiness.
 */
export class CourseMemberValidationRequestValidator extends BaseValidator<CourseMemberValidationRequest> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Validation parameters supplied when checking provider readiness.",
  "properties": {
    "provider_access_token": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Access token or credential used to validate provider ownership",
      "title": "Provider Access Token"
    }
  },
  "title": "CourseMemberValidationRequest",
  "type": "object",
  "x-model-name": "CourseMemberValidationRequest"
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

  validate(data: any): CourseMemberValidationRequest {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseMemberValidationRequest', 'Expected an object');
    }

    // Optional field: provider_access_token
    if ('provider_access_token' in data && data.provider_access_token !== undefined && data.provider_access_token !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseMemberValidationRequest', errors.join('; '));
    }

    return data as CourseMemberValidationRequest;
  }

  safeValidate(data: any): { success: true; data: CourseMemberValidationRequest } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseMemberValidationRequest', String(error)) };
    }
  }
}

/**
 * Validator for CourseProperties
 */
export class CoursePropertiesValidator extends BaseValidator<CourseProperties> {
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
  "title": "CourseProperties",
  "type": "object",
  "x-model-name": "CourseProperties"
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

  validate(data: any): CourseProperties {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseProperties', 'Expected an object');
    }

    // Optional field: gitlab
    if ('gitlab' in data && data.gitlab !== undefined && data.gitlab !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseProperties', errors.join('; '));
    }

    return data as CourseProperties;
  }

  safeValidate(data: any): { success: true; data: CourseProperties } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseProperties', String(error)) };
    }
  }
}

/**
 * Validator for CoursePropertiesGet
 */
export class CoursePropertiesGetValidator extends BaseValidator<CoursePropertiesGet> {
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
  "title": "CoursePropertiesGet",
  "type": "object",
  "x-model-name": "CoursePropertiesGet"
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

  validate(data: any): CoursePropertiesGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CoursePropertiesGet', 'Expected an object');
    }

    // Optional field: gitlab
    if ('gitlab' in data && data.gitlab !== undefined && data.gitlab !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CoursePropertiesGet', errors.join('; '));
    }

    return data as CoursePropertiesGet;
  }

  safeValidate(data: any): { success: true; data: CoursePropertiesGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CoursePropertiesGet', String(error)) };
    }
  }
}

/**
 * Validator for CourseCreate
 */
export class CourseCreateValidator extends BaseValidator<CourseCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseProperties": {
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
      "title": "CourseProperties",
      "type": "object"
    },
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
  "properties": {
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
      "title": "Path",
      "type": "string"
    },
    "course_family_id": {
      "title": "Course Family Id",
      "type": "string"
    },
    "language_code": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Language Code"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "required": [
    "path",
    "course_family_id"
  ],
  "title": "CourseCreate",
  "type": "object",
  "x-model-name": "CourseCreate"
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

  validate(data: any): CourseCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseCreate', 'Expected an object');
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

    // Required field: path
    if (!('path' in data)) {
      errors.push('Missing required field: path');
    } else {
      if (typeof data.path !== 'string') {
        errors.push('Field path must be a string');
      }
    }

    // Required field: course_family_id
    if (!('course_family_id' in data)) {
      errors.push('Missing required field: course_family_id');
    } else {
      if (typeof data.course_family_id !== 'string') {
        errors.push('Field course_family_id must be a string');
      }
    }

    // Optional field: language_code
    if ('language_code' in data && data.language_code !== undefined && data.language_code !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseCreate', errors.join('; '));
    }

    return data as CourseCreate;
  }

  safeValidate(data: any): { success: true; data: CourseCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseCreate', String(error)) };
    }
  }
}

/**
 * Validator for CourseGet
 */
export class CourseGetValidator extends BaseValidator<CourseGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseFamilyGet": {
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
          "title": "Path",
          "type": "string"
        },
        "organization_id": {
          "title": "Organization Id",
          "type": "string"
        },
        "properties": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseFamilyPropertiesGet"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "organization": {
          "anyOf": [
            {
              "$ref": "#/$defs/OrganizationGet"
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
        "path",
        "organization_id"
      ],
      "title": "CourseFamilyGet",
      "type": "object"
    },
    "CourseFamilyPropertiesGet": {
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
      "title": "CourseFamilyPropertiesGet",
      "type": "object"
    },
    "CoursePropertiesGet": {
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
      "title": "CoursePropertiesGet",
      "type": "object"
    },
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
    "OrganizationGet": {
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
    "id": {
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
      "title": "Path",
      "type": "string"
    },
    "course_family_id": {
      "title": "Course Family Id",
      "type": "string"
    },
    "language_code": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Language Code"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CoursePropertiesGet"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
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
    "organization_id": {
      "title": "Organization Id",
      "type": "string"
    },
    "course_family": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseFamilyGet"
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
    "path",
    "course_family_id",
    "organization_id"
  ],
  "title": "CourseGet",
  "type": "object",
  "x-model-name": "CourseGet"
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

  validate(data: any): CourseGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseGet', 'Expected an object');
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

    // Required field: path
    if (!('path' in data)) {
      errors.push('Missing required field: path');
    } else {
      if (typeof data.path !== 'string') {
        errors.push('Field path must be a string');
      }
    }

    // Required field: course_family_id
    if (!('course_family_id' in data)) {
      errors.push('Missing required field: course_family_id');
    } else {
      if (typeof data.course_family_id !== 'string') {
        errors.push('Field course_family_id must be a string');
      }
    }

    // Optional field: language_code
    if ('language_code' in data && data.language_code !== undefined && data.language_code !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
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

    // Required field: organization_id
    if (!('organization_id' in data)) {
      errors.push('Missing required field: organization_id');
    } else {
      if (typeof data.organization_id !== 'string') {
        errors.push('Field organization_id must be a string');
      }
    }

    // Optional field: course_family
    if ('course_family' in data && data.course_family !== undefined && data.course_family !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseGet', errors.join('; '));
    }

    return data as CourseGet;
  }

  safeValidate(data: any): { success: true; data: CourseGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseGet', String(error)) };
    }
  }
}

/**
 * Validator for CourseList
 */
export class CourseListValidator extends BaseValidator<CourseList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CoursePropertiesGet": {
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
      "title": "CoursePropertiesGet",
      "type": "object"
    },
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
  "properties": {
    "id": {
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
      "title": "Title"
    },
    "course_family_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Family Id"
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
    "path": {
      "title": "Path",
      "type": "string"
    },
    "language_code": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Language Code"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CoursePropertiesGet"
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
    "path"
  ],
  "title": "CourseList",
  "type": "object",
  "x-model-name": "CourseList"
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

  validate(data: any): CourseList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseList', 'Expected an object');
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

    // Optional field: course_family_id
    if ('course_family_id' in data && data.course_family_id !== undefined && data.course_family_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: organization_id
    if ('organization_id' in data && data.organization_id !== undefined && data.organization_id !== null) {
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

    // Optional field: language_code
    if ('language_code' in data && data.language_code !== undefined && data.language_code !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseList', errors.join('; '));
    }

    return data as CourseList;
  }

  safeValidate(data: any): { success: true; data: CourseList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseList', String(error)) };
    }
  }
}

/**
 * Validator for CourseUpdate
 */
export class CourseUpdateValidator extends BaseValidator<CourseUpdate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseProperties": {
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
      "title": "CourseProperties",
      "type": "object"
    },
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
    "language_code": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Language Code"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "title": "CourseUpdate",
  "type": "object",
  "x-model-name": "CourseUpdate"
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

  validate(data: any): CourseUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseUpdate', 'Expected an object');
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: language_code
    if ('language_code' in data && data.language_code !== undefined && data.language_code !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseUpdate', errors.join('; '));
    }

    return data as CourseUpdate;
  }

  safeValidate(data: any): { success: true; data: CourseUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseUpdate', String(error)) };
    }
  }
}

/**
 * Validator for CourseQuery
 */
export class CourseQueryValidator extends BaseValidator<CourseQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    "course_family_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Family Id"
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
    "provider_url": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Provider Url"
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
    }
  },
  "title": "CourseQuery",
  "type": "object",
  "x-model-name": "CourseQuery"
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

  validate(data: any): CourseQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseQuery', 'Expected an object');
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

    // Optional field: course_family_id
    if ('course_family_id' in data && data.course_family_id !== undefined && data.course_family_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: organization_id
    if ('organization_id' in data && data.organization_id !== undefined && data.organization_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: provider_url
    if ('provider_url' in data && data.provider_url !== undefined && data.provider_url !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: full_path
    if ('full_path' in data && data.full_path !== undefined && data.full_path !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseQuery', errors.join('; '));
    }

    return data as CourseQuery;
  }

  safeValidate(data: any): { success: true; data: CourseQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseQuery', String(error)) };
    }
  }
}

/**
 * Validator for CourseMemberProperties
 */
export class CourseMemberPropertiesValidator extends BaseValidator<CourseMemberProperties> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseMemberGitLabConfig": {
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
        "full_path_submission": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path Submission"
        }
      },
      "title": "CourseMemberGitLabConfig",
      "type": "object"
    }
  },
  "additionalProperties": true,
  "properties": {
    "gitlab": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseMemberGitLabConfig"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "title": "CourseMemberProperties",
  "type": "object",
  "x-model-name": "CourseMemberProperties"
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

  validate(data: any): CourseMemberProperties {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseMemberProperties', 'Expected an object');
    }

    // Optional field: gitlab
    if ('gitlab' in data && data.gitlab !== undefined && data.gitlab !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseMemberProperties', errors.join('; '));
    }

    return data as CourseMemberProperties;
  }

  safeValidate(data: any): { success: true; data: CourseMemberProperties } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseMemberProperties', String(error)) };
    }
  }
}

/**
 * Validator for CourseMemberCreate
 */
export class CourseMemberCreateValidator extends BaseValidator<CourseMemberCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseMemberGitLabConfig": {
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
        "full_path_submission": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path Submission"
        }
      },
      "title": "CourseMemberGitLabConfig",
      "type": "object"
    },
    "CourseMemberProperties": {
      "additionalProperties": true,
      "properties": {
        "gitlab": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseMemberGitLabConfig"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "CourseMemberProperties",
      "type": "object"
    }
  },
  "properties": {
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
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseMemberProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "user_id": {
      "title": "User Id",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
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
    "course_role_id": {
      "title": "Course Role Id",
      "type": "string"
    }
  },
  "required": [
    "user_id",
    "course_id",
    "course_role_id"
  ],
  "title": "CourseMemberCreate",
  "type": "object",
  "x-model-name": "CourseMemberCreate"
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

  validate(data: any): CourseMemberCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseMemberCreate', 'Expected an object');
    }

    // Optional field: id
    if ('id' in data && data.id !== undefined && data.id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: user_id
    if (!('user_id' in data)) {
      errors.push('Missing required field: user_id');
    } else {
      if (typeof data.user_id !== 'string') {
        errors.push('Field user_id must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Optional field: course_group_id
    if ('course_group_id' in data && data.course_group_id !== undefined && data.course_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: course_role_id
    if (!('course_role_id' in data)) {
      errors.push('Missing required field: course_role_id');
    } else {
      if (typeof data.course_role_id !== 'string') {
        errors.push('Field course_role_id must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseMemberCreate', errors.join('; '));
    }

    return data as CourseMemberCreate;
  }

  safeValidate(data: any): { success: true; data: CourseMemberCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseMemberCreate', String(error)) };
    }
  }
}

/**
 * Validator for CourseMemberGet
 */
export class CourseMemberGetValidator extends BaseValidator<CourseMemberGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseMemberGitLabConfig": {
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
        "full_path_submission": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path Submission"
        }
      },
      "title": "CourseMemberGitLabConfig",
      "type": "object"
    },
    "CourseMemberProperties": {
      "additionalProperties": true,
      "properties": {
        "gitlab": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseMemberGitLabConfig"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "CourseMemberProperties",
      "type": "object"
    },
    "UserList": {
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
          "description": "User unique identifier",
          "title": "Id",
          "type": "string"
        },
        "given_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "User's given name",
          "title": "Given Name"
        },
        "family_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "User's family name",
          "title": "Family Name"
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
          "description": "User's email address",
          "title": "Email"
        },
        "user_type": {
          "anyOf": [
            {
              "$ref": "#/$defs/UserTypeEnum"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Type of user account"
        },
        "username": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Unique username",
          "title": "Username"
        },
        "archived_at": {
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
          "description": "Archive timestamp",
          "title": "Archived At"
        }
      },
      "required": [
        "id"
      ],
      "title": "UserList",
      "type": "object"
    },
    "UserTypeEnum": {
      "enum": [
        "user",
        "token"
      ],
      "title": "UserTypeEnum",
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
      "title": "Id",
      "type": "string"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseMemberProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "user_id": {
      "title": "User Id",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
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
    "course_role_id": {
      "title": "Course Role Id",
      "type": "string"
    },
    "user": {
      "anyOf": [
        {
          "$ref": "#/$defs/UserList"
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
    "user_id",
    "course_id",
    "course_role_id"
  ],
  "title": "CourseMemberGet",
  "type": "object",
  "x-model-name": "CourseMemberGet"
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

  validate(data: any): CourseMemberGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseMemberGet', 'Expected an object');
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

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: user_id
    if (!('user_id' in data)) {
      errors.push('Missing required field: user_id');
    } else {
      if (typeof data.user_id !== 'string') {
        errors.push('Field user_id must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Optional field: course_group_id
    if ('course_group_id' in data && data.course_group_id !== undefined && data.course_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: course_role_id
    if (!('course_role_id' in data)) {
      errors.push('Missing required field: course_role_id');
    } else {
      if (typeof data.course_role_id !== 'string') {
        errors.push('Field course_role_id must be a string');
      }
    }

    // Optional field: user
    if ('user' in data && data.user !== undefined && data.user !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseMemberGet', errors.join('; '));
    }

    return data as CourseMemberGet;
  }

  safeValidate(data: any): { success: true; data: CourseMemberGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseMemberGet', String(error)) };
    }
  }
}

/**
 * Validator for CourseMemberList
 */
export class CourseMemberListValidator extends BaseValidator<CourseMemberList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "UserList": {
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
          "description": "User unique identifier",
          "title": "Id",
          "type": "string"
        },
        "given_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "User's given name",
          "title": "Given Name"
        },
        "family_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "User's family name",
          "title": "Family Name"
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
          "description": "User's email address",
          "title": "Email"
        },
        "user_type": {
          "anyOf": [
            {
              "$ref": "#/$defs/UserTypeEnum"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Type of user account"
        },
        "username": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Unique username",
          "title": "Username"
        },
        "archived_at": {
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
          "description": "Archive timestamp",
          "title": "Archived At"
        }
      },
      "required": [
        "id"
      ],
      "title": "UserList",
      "type": "object"
    },
    "UserTypeEnum": {
      "enum": [
        "user",
        "token"
      ],
      "title": "UserTypeEnum",
      "type": "string"
    }
  },
  "properties": {
    "id": {
      "title": "Id",
      "type": "string"
    },
    "user_id": {
      "title": "User Id",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
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
    "course_role_id": {
      "title": "Course Role Id",
      "type": "string"
    },
    "user": {
      "$ref": "#/$defs/UserList"
    }
  },
  "required": [
    "id",
    "user_id",
    "course_id",
    "course_role_id",
    "user"
  ],
  "title": "CourseMemberList",
  "type": "object",
  "x-model-name": "CourseMemberList"
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

  validate(data: any): CourseMemberList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseMemberList', 'Expected an object');
    }

    // Required field: id
    if (!('id' in data)) {
      errors.push('Missing required field: id');
    } else {
      if (typeof data.id !== 'string') {
        errors.push('Field id must be a string');
      }
    }

    // Required field: user_id
    if (!('user_id' in data)) {
      errors.push('Missing required field: user_id');
    } else {
      if (typeof data.user_id !== 'string') {
        errors.push('Field user_id must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Optional field: course_group_id
    if ('course_group_id' in data && data.course_group_id !== undefined && data.course_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: course_role_id
    if (!('course_role_id' in data)) {
      errors.push('Missing required field: course_role_id');
    } else {
      if (typeof data.course_role_id !== 'string') {
        errors.push('Field course_role_id must be a string');
      }
    }

    // Required field: user
    if (!('user' in data)) {
      errors.push('Missing required field: user');
    } else {
      // Reference field - basic object check
      if (typeof data.user !== 'object') {
        errors.push('Field user must be an object');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseMemberList', errors.join('; '));
    }

    return data as CourseMemberList;
  }

  safeValidate(data: any): { success: true; data: CourseMemberList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseMemberList', String(error)) };
    }
  }
}

/**
 * Validator for CourseMemberUpdate
 */
export class CourseMemberUpdateValidator extends BaseValidator<CourseMemberUpdate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseMemberGitLabConfig": {
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
        "full_path_submission": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path Submission"
        }
      },
      "title": "CourseMemberGitLabConfig",
      "type": "object"
    },
    "CourseMemberProperties": {
      "additionalProperties": true,
      "properties": {
        "gitlab": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseMemberGitLabConfig"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "CourseMemberProperties",
      "type": "object"
    }
  },
  "properties": {
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseMemberProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null
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
    "course_role_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Role Id"
    }
  },
  "title": "CourseMemberUpdate",
  "type": "object",
  "x-model-name": "CourseMemberUpdate"
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

  validate(data: any): CourseMemberUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseMemberUpdate', 'Expected an object');
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_group_id
    if ('course_group_id' in data && data.course_group_id !== undefined && data.course_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_role_id
    if ('course_role_id' in data && data.course_role_id !== undefined && data.course_role_id !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseMemberUpdate', errors.join('; '));
    }

    return data as CourseMemberUpdate;
  }

  safeValidate(data: any): { success: true; data: CourseMemberUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseMemberUpdate', String(error)) };
    }
  }
}

/**
 * Validator for CourseMemberQuery
 */
export class CourseMemberQueryValidator extends BaseValidator<CourseMemberQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseMemberGitLabConfig": {
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
        "full_path_submission": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path Submission"
        }
      },
      "title": "CourseMemberGitLabConfig",
      "type": "object"
    },
    "CourseMemberProperties": {
      "additionalProperties": true,
      "properties": {
        "gitlab": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseMemberGitLabConfig"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "CourseMemberProperties",
      "type": "object"
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
    "course_role_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Role Id"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseMemberProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "given_name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Given Name"
    },
    "family_name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Family Name"
    }
  },
  "title": "CourseMemberQuery",
  "type": "object",
  "x-model-name": "CourseMemberQuery"
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

  validate(data: any): CourseMemberQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseMemberQuery', 'Expected an object');
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

    // Optional field: user_id
    if ('user_id' in data && data.user_id !== undefined && data.user_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_id
    if ('course_id' in data && data.course_id !== undefined && data.course_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_group_id
    if ('course_group_id' in data && data.course_group_id !== undefined && data.course_group_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_role_id
    if ('course_role_id' in data && data.course_role_id !== undefined && data.course_role_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: given_name
    if ('given_name' in data && data.given_name !== undefined && data.given_name !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: family_name
    if ('family_name' in data && data.family_name !== undefined && data.family_name !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseMemberQuery', errors.join('; '));
    }

    return data as CourseMemberQuery;
  }

  safeValidate(data: any): { success: true; data: CourseMemberQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseMemberQuery', String(error)) };
    }
  }
}

/**
 * Validator for CourseExecutionBackendCreate
 */
export class CourseExecutionBackendCreateValidator extends BaseValidator<CourseExecutionBackendCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "execution_backend_id": {
      "title": "Execution Backend Id",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
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
    "execution_backend_id",
    "course_id"
  ],
  "title": "CourseExecutionBackendCreate",
  "type": "object",
  "x-model-name": "CourseExecutionBackendCreate"
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

  validate(data: any): CourseExecutionBackendCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseExecutionBackendCreate', 'Expected an object');
    }

    // Required field: execution_backend_id
    if (!('execution_backend_id' in data)) {
      errors.push('Missing required field: execution_backend_id');
    } else {
      if (typeof data.execution_backend_id !== 'string') {
        errors.push('Field execution_backend_id must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseExecutionBackendCreate', errors.join('; '));
    }

    return data as CourseExecutionBackendCreate;
  }

  safeValidate(data: any): { success: true; data: CourseExecutionBackendCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseExecutionBackendCreate', String(error)) };
    }
  }
}

/**
 * Validator for CourseExecutionBackendGet
 */
export class CourseExecutionBackendGetValidator extends BaseValidator<CourseExecutionBackendGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    "execution_backend_id": {
      "title": "Execution Backend Id",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
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
    "execution_backend_id",
    "course_id"
  ],
  "title": "CourseExecutionBackendGet",
  "type": "object",
  "x-model-name": "CourseExecutionBackendGet"
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

  validate(data: any): CourseExecutionBackendGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseExecutionBackendGet', 'Expected an object');
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

    // Required field: execution_backend_id
    if (!('execution_backend_id' in data)) {
      errors.push('Missing required field: execution_backend_id');
    } else {
      if (typeof data.execution_backend_id !== 'string') {
        errors.push('Field execution_backend_id must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseExecutionBackendGet', errors.join('; '));
    }

    return data as CourseExecutionBackendGet;
  }

  safeValidate(data: any): { success: true; data: CourseExecutionBackendGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseExecutionBackendGet', String(error)) };
    }
  }
}

/**
 * Validator for CourseExecutionBackendList
 */
export class CourseExecutionBackendListValidator extends BaseValidator<CourseExecutionBackendList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "execution_backend_id": {
      "title": "Execution Backend Id",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
    }
  },
  "required": [
    "execution_backend_id",
    "course_id"
  ],
  "title": "CourseExecutionBackendList",
  "type": "object",
  "x-model-name": "CourseExecutionBackendList"
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

  validate(data: any): CourseExecutionBackendList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseExecutionBackendList', 'Expected an object');
    }

    // Required field: execution_backend_id
    if (!('execution_backend_id' in data)) {
      errors.push('Missing required field: execution_backend_id');
    } else {
      if (typeof data.execution_backend_id !== 'string') {
        errors.push('Field execution_backend_id must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseExecutionBackendList', errors.join('; '));
    }

    return data as CourseExecutionBackendList;
  }

  safeValidate(data: any): { success: true; data: CourseExecutionBackendList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseExecutionBackendList', String(error)) };
    }
  }
}

/**
 * Validator for CourseExecutionBackendUpdate
 */
export class CourseExecutionBackendUpdateValidator extends BaseValidator<CourseExecutionBackendUpdate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
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
  "title": "CourseExecutionBackendUpdate",
  "type": "object",
  "x-model-name": "CourseExecutionBackendUpdate"
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

  validate(data: any): CourseExecutionBackendUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseExecutionBackendUpdate', 'Expected an object');
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseExecutionBackendUpdate', errors.join('; '));
    }

    return data as CourseExecutionBackendUpdate;
  }

  safeValidate(data: any): { success: true; data: CourseExecutionBackendUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseExecutionBackendUpdate', String(error)) };
    }
  }
}

/**
 * Validator for CourseExecutionBackendQuery
 */
export class CourseExecutionBackendQueryValidator extends BaseValidator<CourseExecutionBackendQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    "execution_backend_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Execution Backend Id"
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
    },
    "properties": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Properties"
    }
  },
  "title": "CourseExecutionBackendQuery",
  "type": "object",
  "x-model-name": "CourseExecutionBackendQuery"
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

  validate(data: any): CourseExecutionBackendQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseExecutionBackendQuery', 'Expected an object');
    }

    // Optional field: skip
    if ('skip' in data && data.skip !== undefined && data.skip !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: limit
    if ('limit' in data && data.limit !== undefined && data.limit !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: execution_backend_id
    if ('execution_backend_id' in data && data.execution_backend_id !== undefined && data.execution_backend_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_id
    if ('course_id' in data && data.course_id !== undefined && data.course_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseExecutionBackendQuery', errors.join('; '));
    }

    return data as CourseExecutionBackendQuery;
  }

  safeValidate(data: any): { success: true; data: CourseExecutionBackendQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseExecutionBackendQuery', String(error)) };
    }
  }
}

/**
 * Validator for CourseRoleGet
 */
export class CourseRoleGetValidator extends BaseValidator<CourseRoleGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "id": {
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
    }
  },
  "required": [
    "id"
  ],
  "title": "CourseRoleGet",
  "type": "object",
  "x-model-name": "CourseRoleGet"
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

  validate(data: any): CourseRoleGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseRoleGet', 'Expected an object');
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

    if (errors.length > 0) {
      throw new ValidationError('CourseRoleGet', errors.join('; '));
    }

    return data as CourseRoleGet;
  }

  safeValidate(data: any): { success: true; data: CourseRoleGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseRoleGet', String(error)) };
    }
  }
}

/**
 * Validator for CourseRoleList
 */
export class CourseRoleListValidator extends BaseValidator<CourseRoleList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "id": {
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
    }
  },
  "required": [
    "id"
  ],
  "title": "CourseRoleList",
  "type": "object",
  "x-model-name": "CourseRoleList"
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

  validate(data: any): CourseRoleList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseRoleList', 'Expected an object');
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

    if (errors.length > 0) {
      throw new ValidationError('CourseRoleList', errors.join('; '));
    }

    return data as CourseRoleList;
  }

  safeValidate(data: any): { success: true; data: CourseRoleList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseRoleList', String(error)) };
    }
  }
}

/**
 * Validator for CourseRoleQuery
 */
export class CourseRoleQueryValidator extends BaseValidator<CourseRoleQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    }
  },
  "title": "CourseRoleQuery",
  "type": "object",
  "x-model-name": "CourseRoleQuery"
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

  validate(data: any): CourseRoleQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseRoleQuery', 'Expected an object');
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

    if (errors.length > 0) {
      throw new ValidationError('CourseRoleQuery', errors.join('; '));
    }

    return data as CourseRoleQuery;
  }

  safeValidate(data: any): { success: true; data: CourseRoleQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseRoleQuery', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentTypeCreate
 */
export class CourseContentTypeCreateValidator extends BaseValidator<CourseContentTypeCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "slug": {
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
      "default": null,
      "title": "Properties"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
    },
    "course_content_kind_id": {
      "title": "Course Content Kind Id",
      "type": "string"
    }
  },
  "required": [
    "slug",
    "course_id",
    "course_content_kind_id"
  ],
  "title": "CourseContentTypeCreate",
  "type": "object",
  "x-model-name": "CourseContentTypeCreate"
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

  validate(data: any): CourseContentTypeCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentTypeCreate', 'Expected an object');
    }

    // Required field: slug
    if (!('slug' in data)) {
      errors.push('Missing required field: slug');
    } else {
      if (typeof data.slug !== 'string') {
        errors.push('Field slug must be a string');
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

    // Optional field: color
    if ('color' in data && data.color !== undefined && data.color !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Required field: course_content_kind_id
    if (!('course_content_kind_id' in data)) {
      errors.push('Missing required field: course_content_kind_id');
    } else {
      if (typeof data.course_content_kind_id !== 'string') {
        errors.push('Field course_content_kind_id must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentTypeCreate', errors.join('; '));
    }

    return data as CourseContentTypeCreate;
  }

  safeValidate(data: any): { success: true; data: CourseContentTypeCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentTypeCreate', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentTypeGet
 */
export class CourseContentTypeGetValidator extends BaseValidator<CourseContentTypeGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseContentKindGet": {
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
        "has_ascendants": {
          "title": "Has Ascendants",
          "type": "boolean"
        },
        "has_descendants": {
          "title": "Has Descendants",
          "type": "boolean"
        },
        "submittable": {
          "title": "Submittable",
          "type": "boolean"
        },
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
        }
      },
      "required": [
        "has_ascendants",
        "has_descendants",
        "submittable",
        "id"
      ],
      "title": "CourseContentKindGet",
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
    "slug": {
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
    "color": {
      "title": "Color",
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
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
    },
    "course_content_kind_id": {
      "title": "Course Content Kind Id",
      "type": "string"
    },
    "course_content_kind": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseContentKindGet"
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
    "slug",
    "color",
    "course_id",
    "course_content_kind_id"
  ],
  "title": "CourseContentTypeGet",
  "type": "object",
  "x-model-name": "CourseContentTypeGet"
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

  validate(data: any): CourseContentTypeGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentTypeGet', 'Expected an object');
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

    // Required field: slug
    if (!('slug' in data)) {
      errors.push('Missing required field: slug');
    } else {
      if (typeof data.slug !== 'string') {
        errors.push('Field slug must be a string');
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

    // Required field: color
    if (!('color' in data)) {
      errors.push('Missing required field: color');
    } else {
      if (typeof data.color !== 'string') {
        errors.push('Field color must be a string');
      }
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Required field: course_content_kind_id
    if (!('course_content_kind_id' in data)) {
      errors.push('Missing required field: course_content_kind_id');
    } else {
      if (typeof data.course_content_kind_id !== 'string') {
        errors.push('Field course_content_kind_id must be a string');
      }
    }

    // Optional field: course_content_kind
    if ('course_content_kind' in data && data.course_content_kind !== undefined && data.course_content_kind !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentTypeGet', errors.join('; '));
    }

    return data as CourseContentTypeGet;
  }

  safeValidate(data: any): { success: true; data: CourseContentTypeGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentTypeGet', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentTypeList
 */
export class CourseContentTypeListValidator extends BaseValidator<CourseContentTypeList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseContentKindList": {
      "properties": {
        "id": {
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
          "title": "Title"
        },
        "has_ascendants": {
          "title": "Has Ascendants",
          "type": "boolean"
        },
        "has_descendants": {
          "title": "Has Descendants",
          "type": "boolean"
        },
        "submittable": {
          "title": "Submittable",
          "type": "boolean"
        }
      },
      "required": [
        "id",
        "has_ascendants",
        "has_descendants",
        "submittable"
      ],
      "title": "CourseContentKindList",
      "type": "object"
    }
  },
  "properties": {
    "id": {
      "title": "Id",
      "type": "string"
    },
    "slug": {
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
      "title": "Title"
    },
    "color": {
      "title": "Color",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
    },
    "course_content_kind_id": {
      "title": "Course Content Kind Id",
      "type": "string"
    },
    "course_content_kind": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseContentKindList"
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
    "slug",
    "color",
    "course_id",
    "course_content_kind_id"
  ],
  "title": "CourseContentTypeList",
  "type": "object",
  "x-model-name": "CourseContentTypeList"
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

  validate(data: any): CourseContentTypeList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentTypeList', 'Expected an object');
    }

    // Required field: id
    if (!('id' in data)) {
      errors.push('Missing required field: id');
    } else {
      if (typeof data.id !== 'string') {
        errors.push('Field id must be a string');
      }
    }

    // Required field: slug
    if (!('slug' in data)) {
      errors.push('Missing required field: slug');
    } else {
      if (typeof data.slug !== 'string') {
        errors.push('Field slug must be a string');
      }
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: color
    if (!('color' in data)) {
      errors.push('Missing required field: color');
    } else {
      if (typeof data.color !== 'string') {
        errors.push('Field color must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Required field: course_content_kind_id
    if (!('course_content_kind_id' in data)) {
      errors.push('Missing required field: course_content_kind_id');
    } else {
      if (typeof data.course_content_kind_id !== 'string') {
        errors.push('Field course_content_kind_id must be a string');
      }
    }

    // Optional field: course_content_kind
    if ('course_content_kind' in data && data.course_content_kind !== undefined && data.course_content_kind !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentTypeList', errors.join('; '));
    }

    return data as CourseContentTypeList;
  }

  safeValidate(data: any): { success: true; data: CourseContentTypeList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentTypeList', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentTypeUpdate
 */
export class CourseContentTypeUpdateValidator extends BaseValidator<CourseContentTypeUpdate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "slug": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Slug"
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
    "color": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Color"
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
  "title": "CourseContentTypeUpdate",
  "type": "object",
  "x-model-name": "CourseContentTypeUpdate"
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

  validate(data: any): CourseContentTypeUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentTypeUpdate', 'Expected an object');
    }

    // Optional field: slug
    if ('slug' in data && data.slug !== undefined && data.slug !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: color
    if ('color' in data && data.color !== undefined && data.color !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentTypeUpdate', errors.join('; '));
    }

    return data as CourseContentTypeUpdate;
  }

  safeValidate(data: any): { success: true; data: CourseContentTypeUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentTypeUpdate', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentTypeQuery
 */
export class CourseContentTypeQueryValidator extends BaseValidator<CourseContentTypeQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    "slug": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Slug"
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
    "color": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Color"
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
    },
    "properties": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Properties"
    },
    "course_content_kind_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Content Kind Id"
    }
  },
  "title": "CourseContentTypeQuery",
  "type": "object",
  "x-model-name": "CourseContentTypeQuery"
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

  validate(data: any): CourseContentTypeQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentTypeQuery', 'Expected an object');
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

    // Optional field: slug
    if ('slug' in data && data.slug !== undefined && data.slug !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: color
    if ('color' in data && data.color !== undefined && data.color !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_id
    if ('course_id' in data && data.course_id !== undefined && data.course_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_content_kind_id
    if ('course_content_kind_id' in data && data.course_content_kind_id !== undefined && data.course_content_kind_id !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentTypeQuery', errors.join('; '));
    }

    return data as CourseContentTypeQuery;
  }

  safeValidate(data: any): { success: true; data: CourseContentTypeQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentTypeQuery', String(error)) };
    }
  }
}

/**
 * Validator for CourseGroupCreate
 */
export class CourseGroupCreateValidator extends BaseValidator<CourseGroupCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    "course_id": {
      "title": "Course Id",
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
    "course_id"
  ],
  "title": "CourseGroupCreate",
  "type": "object",
  "x-model-name": "CourseGroupCreate"
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

  validate(data: any): CourseGroupCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseGroupCreate', 'Expected an object');
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseGroupCreate', errors.join('; '));
    }

    return data as CourseGroupCreate;
  }

  safeValidate(data: any): { success: true; data: CourseGroupCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseGroupCreate', String(error)) };
    }
  }
}

/**
 * Validator for CourseGroupGet
 */
export class CourseGroupGetValidator extends BaseValidator<CourseGroupGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    "course_id": {
      "title": "Course Id",
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
    },
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
    }
  },
  "required": [
    "course_id",
    "id"
  ],
  "title": "CourseGroupGet",
  "type": "object",
  "x-model-name": "CourseGroupGet"
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

  validate(data: any): CourseGroupGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseGroupGet', 'Expected an object');
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
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

    if (errors.length > 0) {
      throw new ValidationError('CourseGroupGet', errors.join('; '));
    }

    return data as CourseGroupGet;
  }

  safeValidate(data: any): { success: true; data: CourseGroupGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseGroupGet', String(error)) };
    }
  }
}

/**
 * Validator for CourseGroupList
 */
export class CourseGroupListValidator extends BaseValidator<CourseGroupList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "id": {
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
      "title": "Title"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
    }
  },
  "required": [
    "id",
    "course_id"
  ],
  "title": "CourseGroupList",
  "type": "object",
  "x-model-name": "CourseGroupList"
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

  validate(data: any): CourseGroupList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseGroupList', 'Expected an object');
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

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseGroupList', errors.join('; '));
    }

    return data as CourseGroupList;
  }

  safeValidate(data: any): { success: true; data: CourseGroupList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseGroupList', String(error)) };
    }
  }
}

/**
 * Validator for CourseGroupUpdate
 */
export class CourseGroupUpdateValidator extends BaseValidator<CourseGroupUpdate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
  "title": "CourseGroupUpdate",
  "type": "object",
  "x-model-name": "CourseGroupUpdate"
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

  validate(data: any): CourseGroupUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseGroupUpdate', 'Expected an object');
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_id
    if ('course_id' in data && data.course_id !== undefined && data.course_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseGroupUpdate', errors.join('; '));
    }

    return data as CourseGroupUpdate;
  }

  safeValidate(data: any): { success: true; data: CourseGroupUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseGroupUpdate', String(error)) };
    }
  }
}

/**
 * Validator for CourseGroupQuery
 */
export class CourseGroupQueryValidator extends BaseValidator<CourseGroupQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    },
    "properties": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Properties"
    }
  },
  "title": "CourseGroupQuery",
  "type": "object",
  "x-model-name": "CourseGroupQuery"
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

  validate(data: any): CourseGroupQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseGroupQuery', 'Expected an object');
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

    // Optional field: course_id
    if ('course_id' in data && data.course_id !== undefined && data.course_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseGroupQuery', errors.join('; '));
    }

    return data as CourseGroupQuery;
  }

  safeValidate(data: any): { success: true; data: CourseGroupQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseGroupQuery', String(error)) };
    }
  }
}

/**
 * Repository information for course content in lecturer view.
 */
export class CourseContentRepositoryLecturerGetValidator extends BaseValidator<CourseContentRepositoryLecturerGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Repository information for course content in lecturer view.",
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
    }
  },
  "title": "CourseContentRepositoryLecturerGet",
  "type": "object",
  "x-model-name": "CourseContentRepositoryLecturerGet"
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

  validate(data: any): CourseContentRepositoryLecturerGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentRepositoryLecturerGet', 'Expected an object');
    }

    // Optional field: url
    if ('url' in data && data.url !== undefined && data.url !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: full_path
    if ('full_path' in data && data.full_path !== undefined && data.full_path !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentRepositoryLecturerGet', errors.join('; '));
    }

    return data as CourseContentRepositoryLecturerGet;
  }

  safeValidate(data: any): { success: true; data: CourseContentRepositoryLecturerGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentRepositoryLecturerGet', String(error)) };
    }
  }
}

/**
 * DTO for lecturer GET of course content with course repository info.
 */
export class CourseContentLecturerGetValidator extends BaseValidator<CourseContentLecturerGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseContentKindGet": {
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
        "has_ascendants": {
          "title": "Has Ascendants",
          "type": "boolean"
        },
        "has_descendants": {
          "title": "Has Descendants",
          "type": "boolean"
        },
        "submittable": {
          "title": "Submittable",
          "type": "boolean"
        },
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
        }
      },
      "required": [
        "has_ascendants",
        "has_descendants",
        "submittable",
        "id"
      ],
      "title": "CourseContentKindGet",
      "type": "object"
    },
    "CourseContentRepositoryLecturerGet": {
      "description": "Repository information for course content in lecturer view.",
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
        }
      },
      "title": "CourseContentRepositoryLecturerGet",
      "type": "object"
    },
    "CourseContentTypeGet": {
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
        "slug": {
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
        "color": {
          "title": "Color",
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
        },
        "course_id": {
          "title": "Course Id",
          "type": "string"
        },
        "course_content_kind_id": {
          "title": "Course Content Kind Id",
          "type": "string"
        },
        "course_content_kind": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseContentKindGet"
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
        "slug",
        "color",
        "course_id",
        "course_content_kind_id"
      ],
      "title": "CourseContentTypeGet",
      "type": "object"
    }
  },
  "description": "DTO for lecturer GET of course content with course repository info.",
  "properties": {
    "id": {
      "title": "Id",
      "type": "string"
    },
    "archived_at": {
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
      "title": "Archived At"
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
      "title": "Path",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
    },
    "course_content_type_id": {
      "title": "Course Content Type Id",
      "type": "string"
    },
    "course_content_kind_id": {
      "title": "Course Content Kind Id",
      "type": "string"
    },
    "position": {
      "title": "Position",
      "type": "number"
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
      "title": "Max Submissions"
    },
    "execution_backend_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Execution Backend Id"
    },
    "is_submittable": {
      "default": false,
      "title": "Is Submittable",
      "type": "boolean"
    },
    "has_deployment": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Has Deployment"
    },
    "deployment_status": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Deployment Status"
    },
    "course_content_type": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseContentTypeGet"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "repository": {
      "$ref": "#/$defs/CourseContentRepositoryLecturerGet"
    }
  },
  "required": [
    "id",
    "path",
    "course_id",
    "course_content_type_id",
    "course_content_kind_id",
    "position",
    "repository"
  ],
  "title": "CourseContentLecturerGet",
  "type": "object",
  "x-model-name": "CourseContentLecturerGet"
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

  validate(data: any): CourseContentLecturerGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentLecturerGet', 'Expected an object');
    }

    // Required field: id
    if (!('id' in data)) {
      errors.push('Missing required field: id');
    } else {
      if (typeof data.id !== 'string') {
        errors.push('Field id must be a string');
      }
    }

    // Optional field: archived_at
    if ('archived_at' in data && data.archived_at !== undefined && data.archived_at !== null) {
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

    // Required field: path
    if (!('path' in data)) {
      errors.push('Missing required field: path');
    } else {
      if (typeof data.path !== 'string') {
        errors.push('Field path must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Required field: course_content_type_id
    if (!('course_content_type_id' in data)) {
      errors.push('Missing required field: course_content_type_id');
    } else {
      if (typeof data.course_content_type_id !== 'string') {
        errors.push('Field course_content_type_id must be a string');
      }
    }

    // Required field: course_content_kind_id
    if (!('course_content_kind_id' in data)) {
      errors.push('Missing required field: course_content_kind_id');
    } else {
      if (typeof data.course_content_kind_id !== 'string') {
        errors.push('Field course_content_kind_id must be a string');
      }
    }

    // Required field: position
    if (!('position' in data)) {
      errors.push('Missing required field: position');
    } else {
      if (typeof data.position !== 'number') {
        errors.push('Field position must be a number');
      }
    }

    // Optional field: max_group_size
    if ('max_group_size' in data && data.max_group_size !== undefined && data.max_group_size !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_test_runs
    if ('max_test_runs' in data && data.max_test_runs !== undefined && data.max_test_runs !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_submissions
    if ('max_submissions' in data && data.max_submissions !== undefined && data.max_submissions !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: execution_backend_id
    if ('execution_backend_id' in data && data.execution_backend_id !== undefined && data.execution_backend_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: is_submittable
    if ('is_submittable' in data && data.is_submittable !== undefined && data.is_submittable !== null) {
      if (typeof data.is_submittable !== 'boolean') {
        errors.push('Field is_submittable must be a boolean');
      }
    }

    // Optional field: has_deployment
    if ('has_deployment' in data && data.has_deployment !== undefined && data.has_deployment !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: deployment_status
    if ('deployment_status' in data && data.deployment_status !== undefined && data.deployment_status !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_content_type
    if ('course_content_type' in data && data.course_content_type !== undefined && data.course_content_type !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: repository
    if (!('repository' in data)) {
      errors.push('Missing required field: repository');
    } else {
      // Reference field - basic object check
      if (typeof data.repository !== 'object') {
        errors.push('Field repository must be an object');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentLecturerGet', errors.join('; '));
    }

    return data as CourseContentLecturerGet;
  }

  safeValidate(data: any): { success: true; data: CourseContentLecturerGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentLecturerGet', String(error)) };
    }
  }
}

/**
 * DTO for lecturer list of course content with course repository info.
 */
export class CourseContentLecturerListValidator extends BaseValidator<CourseContentLecturerList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseContentKindList": {
      "properties": {
        "id": {
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
          "title": "Title"
        },
        "has_ascendants": {
          "title": "Has Ascendants",
          "type": "boolean"
        },
        "has_descendants": {
          "title": "Has Descendants",
          "type": "boolean"
        },
        "submittable": {
          "title": "Submittable",
          "type": "boolean"
        }
      },
      "required": [
        "id",
        "has_ascendants",
        "has_descendants",
        "submittable"
      ],
      "title": "CourseContentKindList",
      "type": "object"
    },
    "CourseContentRepositoryLecturerGet": {
      "description": "Repository information for course content in lecturer view.",
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
        }
      },
      "title": "CourseContentRepositoryLecturerGet",
      "type": "object"
    },
    "CourseContentTypeList": {
      "properties": {
        "id": {
          "title": "Id",
          "type": "string"
        },
        "slug": {
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
          "title": "Title"
        },
        "color": {
          "title": "Color",
          "type": "string"
        },
        "course_id": {
          "title": "Course Id",
          "type": "string"
        },
        "course_content_kind_id": {
          "title": "Course Content Kind Id",
          "type": "string"
        },
        "course_content_kind": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseContentKindList"
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
        "slug",
        "color",
        "course_id",
        "course_content_kind_id"
      ],
      "title": "CourseContentTypeList",
      "type": "object"
    }
  },
  "description": "DTO for lecturer list of course content with course repository info.",
  "properties": {
    "id": {
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
      "title": "Title"
    },
    "path": {
      "title": "Path",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
    },
    "course_content_type_id": {
      "title": "Course Content Type Id",
      "type": "string"
    },
    "course_content_kind_id": {
      "title": "Course Content Kind Id",
      "type": "string"
    },
    "position": {
      "title": "Position",
      "type": "number"
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
      "title": "Max Submissions"
    },
    "execution_backend_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Execution Backend Id"
    },
    "is_submittable": {
      "default": false,
      "title": "Is Submittable",
      "type": "boolean"
    },
    "has_deployment": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Has Deployment"
    },
    "deployment_status": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Deployment Status"
    },
    "course_content_type": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseContentTypeList"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "repository": {
      "$ref": "#/$defs/CourseContentRepositoryLecturerGet"
    }
  },
  "required": [
    "id",
    "path",
    "course_id",
    "course_content_type_id",
    "course_content_kind_id",
    "position",
    "repository"
  ],
  "title": "CourseContentLecturerList",
  "type": "object",
  "x-model-name": "CourseContentLecturerList"
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

  validate(data: any): CourseContentLecturerList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentLecturerList', 'Expected an object');
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

    // Required field: path
    if (!('path' in data)) {
      errors.push('Missing required field: path');
    } else {
      if (typeof data.path !== 'string') {
        errors.push('Field path must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Required field: course_content_type_id
    if (!('course_content_type_id' in data)) {
      errors.push('Missing required field: course_content_type_id');
    } else {
      if (typeof data.course_content_type_id !== 'string') {
        errors.push('Field course_content_type_id must be a string');
      }
    }

    // Required field: course_content_kind_id
    if (!('course_content_kind_id' in data)) {
      errors.push('Missing required field: course_content_kind_id');
    } else {
      if (typeof data.course_content_kind_id !== 'string') {
        errors.push('Field course_content_kind_id must be a string');
      }
    }

    // Required field: position
    if (!('position' in data)) {
      errors.push('Missing required field: position');
    } else {
      if (typeof data.position !== 'number') {
        errors.push('Field position must be a number');
      }
    }

    // Optional field: max_group_size
    if ('max_group_size' in data && data.max_group_size !== undefined && data.max_group_size !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_test_runs
    if ('max_test_runs' in data && data.max_test_runs !== undefined && data.max_test_runs !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_submissions
    if ('max_submissions' in data && data.max_submissions !== undefined && data.max_submissions !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: execution_backend_id
    if ('execution_backend_id' in data && data.execution_backend_id !== undefined && data.execution_backend_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: is_submittable
    if ('is_submittable' in data && data.is_submittable !== undefined && data.is_submittable !== null) {
      if (typeof data.is_submittable !== 'boolean') {
        errors.push('Field is_submittable must be a boolean');
      }
    }

    // Optional field: has_deployment
    if ('has_deployment' in data && data.has_deployment !== undefined && data.has_deployment !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: deployment_status
    if ('deployment_status' in data && data.deployment_status !== undefined && data.deployment_status !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_content_type
    if ('course_content_type' in data && data.course_content_type !== undefined && data.course_content_type !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: repository
    if (!('repository' in data)) {
      errors.push('Missing required field: repository');
    } else {
      // Reference field - basic object check
      if (typeof data.repository !== 'object') {
        errors.push('Field repository must be an object');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentLecturerList', errors.join('; '));
    }

    return data as CourseContentLecturerList;
  }

  safeValidate(data: any): { success: true; data: CourseContentLecturerList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentLecturerList', String(error)) };
    }
  }
}

/**
 * Query parameters for lecturer course content.
 */
export class CourseContentLecturerQueryValidator extends BaseValidator<CourseContentLecturerQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Query parameters for lecturer course content.",
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
    },
    "course_content_type_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Content Type Id"
    },
    "archived": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Archived"
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
      "title": "Max Submissions"
    },
    "execution_backend_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Execution Backend Id"
    },
    "has_deployment": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Filter by whether content has a deployment",
      "title": "Has Deployment"
    }
  },
  "title": "CourseContentLecturerQuery",
  "type": "object",
  "x-model-name": "CourseContentLecturerQuery"
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

  validate(data: any): CourseContentLecturerQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentLecturerQuery', 'Expected an object');
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

    // Optional field: path
    if ('path' in data && data.path !== undefined && data.path !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_id
    if ('course_id' in data && data.course_id !== undefined && data.course_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_content_type_id
    if ('course_content_type_id' in data && data.course_content_type_id !== undefined && data.course_content_type_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: archived
    if ('archived' in data && data.archived !== undefined && data.archived !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: position
    if ('position' in data && data.position !== undefined && data.position !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_group_size
    if ('max_group_size' in data && data.max_group_size !== undefined && data.max_group_size !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_test_runs
    if ('max_test_runs' in data && data.max_test_runs !== undefined && data.max_test_runs !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_submissions
    if ('max_submissions' in data && data.max_submissions !== undefined && data.max_submissions !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: execution_backend_id
    if ('execution_backend_id' in data && data.execution_backend_id !== undefined && data.execution_backend_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: has_deployment
    if ('has_deployment' in data && data.has_deployment !== undefined && data.has_deployment !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentLecturerQuery', errors.join('; '));
    }

    return data as CourseContentLecturerQuery;
  }

  safeValidate(data: any): { success: true; data: CourseContentLecturerQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentLecturerQuery', String(error)) };
    }
  }
}

/**
 * Validator for GradedByCourseMember
 */
export class GradedByCourseMemberValidator extends BaseValidator<GradedByCourseMember> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "GradingAuthor": {
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
      "title": "GradingAuthor",
      "type": "object"
    }
  },
  "properties": {
    "course_role_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Role Id"
    },
    "user_id": {
      "title": "User Id",
      "type": "string"
    },
    "user": {
      "anyOf": [
        {
          "$ref": "#/$defs/GradingAuthor"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "required": [
    "user_id"
  ],
  "title": "GradedByCourseMember",
  "type": "object",
  "x-model-name": "GradedByCourseMember"
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

  validate(data: any): GradedByCourseMember {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('GradedByCourseMember', 'Expected an object');
    }

    // Optional field: course_role_id
    if ('course_role_id' in data && data.course_role_id !== undefined && data.course_role_id !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: user_id
    if (!('user_id' in data)) {
      errors.push('Missing required field: user_id');
    } else {
      if (typeof data.user_id !== 'string') {
        errors.push('Field user_id must be a string');
      }
    }

    // Optional field: user
    if ('user' in data && data.user !== undefined && data.user !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('GradedByCourseMember', errors.join('; '));
    }

    return data as GradedByCourseMember;
  }

  safeValidate(data: any): { success: true; data: GradedByCourseMember } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('GradedByCourseMember', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentStudentProperties
 */
export class CourseContentStudentPropertiesValidator extends BaseValidator<CourseContentStudentProperties> {
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
  "title": "CourseContentStudentProperties",
  "type": "object",
  "x-model-name": "CourseContentStudentProperties"
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

  validate(data: any): CourseContentStudentProperties {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentStudentProperties', 'Expected an object');
    }

    // Optional field: gitlab
    if ('gitlab' in data && data.gitlab !== undefined && data.gitlab !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentStudentProperties', errors.join('; '));
    }

    return data as CourseContentStudentProperties;
  }

  safeValidate(data: any): { success: true; data: CourseContentStudentProperties } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentStudentProperties', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentStudentGet
 */
export class CourseContentStudentGetValidator extends BaseValidator<CourseContentStudentGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseContentKindGet": {
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
        "has_ascendants": {
          "title": "Has Ascendants",
          "type": "boolean"
        },
        "has_descendants": {
          "title": "Has Descendants",
          "type": "boolean"
        },
        "submittable": {
          "title": "Submittable",
          "type": "boolean"
        },
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
        }
      },
      "required": [
        "has_ascendants",
        "has_descendants",
        "submittable",
        "id"
      ],
      "title": "CourseContentKindGet",
      "type": "object"
    },
    "CourseContentTypeGet": {
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
        "slug": {
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
        "color": {
          "title": "Color",
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
        },
        "course_id": {
          "title": "Course Id",
          "type": "string"
        },
        "course_content_kind_id": {
          "title": "Course Content Kind Id",
          "type": "string"
        },
        "course_content_kind": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseContentKindGet"
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
        "slug",
        "color",
        "course_id",
        "course_content_kind_id"
      ],
      "title": "CourseContentTypeGet",
      "type": "object"
    },
    "GradedByCourseMember": {
      "properties": {
        "course_role_id": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Course Role Id"
        },
        "user_id": {
          "title": "User Id",
          "type": "string"
        },
        "user": {
          "anyOf": [
            {
              "$ref": "#/$defs/GradingAuthor"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "required": [
        "user_id"
      ],
      "title": "GradedByCourseMember",
      "type": "object"
    },
    "GradingAuthor": {
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
      "title": "GradingAuthor",
      "type": "object"
    },
    "GradingStatus": {
      "description": "Enumeration for grading status values.",
      "enum": [
        0,
        1,
        2,
        3
      ],
      "title": "GradingStatus",
      "type": "integer"
    },
    "ResultStudentList": {
      "properties": {
        "execution_backend_id": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Execution Backend Id"
        },
        "test_system_id": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Test System Id"
        },
        "version_identifier": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Version Identifier"
        },
        "status": {
          "anyOf": [
            {
              "$ref": "#/$defs/TaskStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "result": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Result"
        },
        "result_json": {
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
          "title": "Result Json"
        },
        "submit": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Submit"
        }
      },
      "title": "ResultStudentList",
      "type": "object"
    },
    "SubmissionGroupGradingList": {
      "description": "List view of grading.",
      "properties": {
        "id": {
          "title": "Id",
          "type": "string"
        },
        "submission_group_id": {
          "title": "Submission Group Id",
          "type": "string"
        },
        "graded_by_course_member_id": {
          "title": "Graded By Course Member Id",
          "type": "string"
        },
        "result_id": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Result Id"
        },
        "grading": {
          "title": "Grading",
          "type": "number"
        },
        "status": {
          "$ref": "#/$defs/GradingStatus"
        },
        "feedback": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Feedback"
        },
        "created_at": {
          "format": "date-time",
          "title": "Created At",
          "type": "string"
        },
        "graded_by_course_member": {
          "anyOf": [
            {
              "$ref": "#/$defs/GradedByCourseMember"
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
        "submission_group_id",
        "graded_by_course_member_id",
        "grading",
        "status",
        "created_at"
      ],
      "title": "SubmissionGroupGradingList",
      "type": "object"
    },
    "SubmissionGroupMemberBasic": {
      "description": "Basic member information",
      "properties": {
        "id": {
          "title": "Id",
          "type": "string"
        },
        "user_id": {
          "title": "User Id",
          "type": "string"
        },
        "course_member_id": {
          "title": "Course Member Id",
          "type": "string"
        },
        "username": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Username"
        },
        "full_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Name"
        }
      },
      "required": [
        "id",
        "user_id",
        "course_member_id"
      ],
      "title": "SubmissionGroupMemberBasic",
      "type": "object"
    },
    "SubmissionGroupRepository": {
      "description": "Repository information for a submission group",
      "properties": {
        "provider": {
          "default": "gitlab",
          "title": "Provider",
          "type": "string"
        },
        "url": {
          "title": "Url",
          "type": "string"
        },
        "full_path": {
          "title": "Full Path",
          "type": "string"
        },
        "clone_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Clone Url"
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
        }
      },
      "required": [
        "url",
        "full_path"
      ],
      "title": "SubmissionGroupRepository",
      "type": "object"
    },
    "SubmissionGroupStudentGet": {
      "description": "Detailed submission group view including grading history.",
      "properties": {
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
        "course_content_title": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Course Content Title"
        },
        "course_content_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Course Content Path"
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
          "title": "Example Identifier"
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
          "title": "Max Group Size"
        },
        "current_group_size": {
          "default": 1,
          "title": "Current Group Size",
          "type": "integer"
        },
        "members": {
          "default": [],
          "items": {
            "$ref": "#/$defs/SubmissionGroupMemberBasic"
          },
          "title": "Members",
          "type": "array"
        },
        "repository": {
          "anyOf": [
            {
              "$ref": "#/$defs/SubmissionGroupRepository"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "status": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Status"
        },
        "grading": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Grading"
        },
        "count": {
          "default": 0,
          "title": "Count",
          "type": "integer"
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
          "title": "Max Submissions"
        },
        "unread_message_count": {
          "default": 0,
          "title": "Unread Message Count",
          "type": "integer"
        },
        "gradings": {
          "items": {
            "$ref": "#/$defs/SubmissionGroupGradingList"
          },
          "title": "Gradings",
          "type": "array"
        }
      },
      "title": "SubmissionGroupStudentGet",
      "type": "object"
    },
    "TaskStatus": {
      "description": "Task execution status enumeration.",
      "enum": [
        "queued",
        "started",
        "finished",
        "failed",
        "deferred",
        "cancelled"
      ],
      "title": "TaskStatus",
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
      "title": "Id",
      "type": "string"
    },
    "archived_at": {
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
      "title": "Archived At"
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
      "title": "Path",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
    },
    "course_content_type_id": {
      "title": "Course Content Type Id",
      "type": "string"
    },
    "course_content_kind_id": {
      "title": "Course Content Kind Id",
      "type": "string"
    },
    "position": {
      "title": "Position",
      "type": "number"
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
      "title": "Max Group Size"
    },
    "submitted": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Submitted"
    },
    "course_content_types": {
      "$ref": "#/$defs/CourseContentTypeGet"
    },
    "result_count": {
      "title": "Result Count",
      "type": "integer"
    },
    "submission_count": {
      "title": "Submission Count",
      "type": "integer"
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
      "title": "Max Test Runs"
    },
    "unread_message_count": {
      "default": 0,
      "title": "Unread Message Count",
      "type": "integer"
    },
    "result": {
      "anyOf": [
        {
          "$ref": "#/$defs/ResultStudentList"
        },
        {
          "type": "null"
        }
      ],
      "default": null
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
    "color": {
      "title": "Color",
      "type": "string"
    },
    "submission_group": {
      "anyOf": [
        {
          "$ref": "#/$defs/SubmissionGroupStudentGet"
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
    "path",
    "course_id",
    "course_content_type_id",
    "course_content_kind_id",
    "position",
    "course_content_types",
    "result_count",
    "submission_count",
    "color"
  ],
  "title": "CourseContentStudentGet",
  "type": "object",
  "x-model-name": "CourseContentStudentGet"
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

  validate(data: any): CourseContentStudentGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentStudentGet', 'Expected an object');
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

    // Optional field: archived_at
    if ('archived_at' in data && data.archived_at !== undefined && data.archived_at !== null) {
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

    // Required field: path
    if (!('path' in data)) {
      errors.push('Missing required field: path');
    } else {
      if (typeof data.path !== 'string') {
        errors.push('Field path must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Required field: course_content_type_id
    if (!('course_content_type_id' in data)) {
      errors.push('Missing required field: course_content_type_id');
    } else {
      if (typeof data.course_content_type_id !== 'string') {
        errors.push('Field course_content_type_id must be a string');
      }
    }

    // Required field: course_content_kind_id
    if (!('course_content_kind_id' in data)) {
      errors.push('Missing required field: course_content_kind_id');
    } else {
      if (typeof data.course_content_kind_id !== 'string') {
        errors.push('Field course_content_kind_id must be a string');
      }
    }

    // Required field: position
    if (!('position' in data)) {
      errors.push('Missing required field: position');
    } else {
      if (typeof data.position !== 'number') {
        errors.push('Field position must be a number');
      }
    }

    // Optional field: max_group_size
    if ('max_group_size' in data && data.max_group_size !== undefined && data.max_group_size !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: submitted
    if ('submitted' in data && data.submitted !== undefined && data.submitted !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: course_content_types
    if (!('course_content_types' in data)) {
      errors.push('Missing required field: course_content_types');
    } else {
      // Reference field - basic object check
      if (typeof data.course_content_types !== 'object') {
        errors.push('Field course_content_types must be an object');
      }
    }

    // Required field: result_count
    if (!('result_count' in data)) {
      errors.push('Missing required field: result_count');
    } else {
      if (typeof data.result_count !== 'number') {
        errors.push('Field result_count must be a number');
      }
    }

    // Required field: submission_count
    if (!('submission_count' in data)) {
      errors.push('Missing required field: submission_count');
    } else {
      if (typeof data.submission_count !== 'number') {
        errors.push('Field submission_count must be a number');
      }
    }

    // Optional field: max_test_runs
    if ('max_test_runs' in data && data.max_test_runs !== undefined && data.max_test_runs !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: unread_message_count
    if ('unread_message_count' in data && data.unread_message_count !== undefined && data.unread_message_count !== null) {
      if (typeof data.unread_message_count !== 'number') {
        errors.push('Field unread_message_count must be a number');
      }
    }

    // Optional field: result
    if ('result' in data && data.result !== undefined && data.result !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: directory
    if ('directory' in data && data.directory !== undefined && data.directory !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: color
    if (!('color' in data)) {
      errors.push('Missing required field: color');
    } else {
      if (typeof data.color !== 'string') {
        errors.push('Field color must be a string');
      }
    }

    // Optional field: submission_group
    if ('submission_group' in data && data.submission_group !== undefined && data.submission_group !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentStudentGet', errors.join('; '));
    }

    return data as CourseContentStudentGet;
  }

  safeValidate(data: any): { success: true; data: CourseContentStudentGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentStudentGet', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentStudentList
 */
export class CourseContentStudentListValidator extends BaseValidator<CourseContentStudentList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseContentKindList": {
      "properties": {
        "id": {
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
          "title": "Title"
        },
        "has_ascendants": {
          "title": "Has Ascendants",
          "type": "boolean"
        },
        "has_descendants": {
          "title": "Has Descendants",
          "type": "boolean"
        },
        "submittable": {
          "title": "Submittable",
          "type": "boolean"
        }
      },
      "required": [
        "id",
        "has_ascendants",
        "has_descendants",
        "submittable"
      ],
      "title": "CourseContentKindList",
      "type": "object"
    },
    "CourseContentTypeList": {
      "properties": {
        "id": {
          "title": "Id",
          "type": "string"
        },
        "slug": {
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
          "title": "Title"
        },
        "color": {
          "title": "Color",
          "type": "string"
        },
        "course_id": {
          "title": "Course Id",
          "type": "string"
        },
        "course_content_kind_id": {
          "title": "Course Content Kind Id",
          "type": "string"
        },
        "course_content_kind": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseContentKindList"
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
        "slug",
        "color",
        "course_id",
        "course_content_kind_id"
      ],
      "title": "CourseContentTypeList",
      "type": "object"
    },
    "ResultStudentList": {
      "properties": {
        "execution_backend_id": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Execution Backend Id"
        },
        "test_system_id": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Test System Id"
        },
        "version_identifier": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Version Identifier"
        },
        "status": {
          "anyOf": [
            {
              "$ref": "#/$defs/TaskStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "result": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Result"
        },
        "result_json": {
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
          "title": "Result Json"
        },
        "submit": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Submit"
        }
      },
      "title": "ResultStudentList",
      "type": "object"
    },
    "SubmissionGroupMemberBasic": {
      "description": "Basic member information",
      "properties": {
        "id": {
          "title": "Id",
          "type": "string"
        },
        "user_id": {
          "title": "User Id",
          "type": "string"
        },
        "course_member_id": {
          "title": "Course Member Id",
          "type": "string"
        },
        "username": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Username"
        },
        "full_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Name"
        }
      },
      "required": [
        "id",
        "user_id",
        "course_member_id"
      ],
      "title": "SubmissionGroupMemberBasic",
      "type": "object"
    },
    "SubmissionGroupRepository": {
      "description": "Repository information for a submission group",
      "properties": {
        "provider": {
          "default": "gitlab",
          "title": "Provider",
          "type": "string"
        },
        "url": {
          "title": "Url",
          "type": "string"
        },
        "full_path": {
          "title": "Full Path",
          "type": "string"
        },
        "clone_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Clone Url"
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
        }
      },
      "required": [
        "url",
        "full_path"
      ],
      "title": "SubmissionGroupRepository",
      "type": "object"
    },
    "SubmissionGroupStudentList": {
      "description": "Submission group data for course contents (list view).",
      "properties": {
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
        "course_content_title": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Course Content Title"
        },
        "course_content_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Course Content Path"
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
          "title": "Example Identifier"
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
          "title": "Max Group Size"
        },
        "current_group_size": {
          "default": 1,
          "title": "Current Group Size",
          "type": "integer"
        },
        "members": {
          "default": [],
          "items": {
            "$ref": "#/$defs/SubmissionGroupMemberBasic"
          },
          "title": "Members",
          "type": "array"
        },
        "repository": {
          "anyOf": [
            {
              "$ref": "#/$defs/SubmissionGroupRepository"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "status": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Status"
        },
        "grading": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Grading"
        },
        "count": {
          "default": 0,
          "title": "Count",
          "type": "integer"
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
          "title": "Max Submissions"
        },
        "unread_message_count": {
          "default": 0,
          "title": "Unread Message Count",
          "type": "integer"
        }
      },
      "title": "SubmissionGroupStudentList",
      "type": "object"
    },
    "TaskStatus": {
      "description": "Task execution status enumeration.",
      "enum": [
        "queued",
        "started",
        "finished",
        "failed",
        "deferred",
        "cancelled"
      ],
      "title": "TaskStatus",
      "type": "string"
    }
  },
  "properties": {
    "id": {
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
      "title": "Title"
    },
    "path": {
      "title": "Path",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
    },
    "course_content_type_id": {
      "title": "Course Content Type Id",
      "type": "string"
    },
    "course_content_kind_id": {
      "title": "Course Content Kind Id",
      "type": "string"
    },
    "position": {
      "title": "Position",
      "type": "number"
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
      "title": "Max Group Size"
    },
    "submitted": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Submitted"
    },
    "course_content_type": {
      "$ref": "#/$defs/CourseContentTypeList"
    },
    "result_count": {
      "title": "Result Count",
      "type": "integer"
    },
    "submission_count": {
      "title": "Submission Count",
      "type": "integer"
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
      "title": "Max Test Runs"
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
    "color": {
      "title": "Color",
      "type": "string"
    },
    "result": {
      "anyOf": [
        {
          "$ref": "#/$defs/ResultStudentList"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "submission_group": {
      "anyOf": [
        {
          "$ref": "#/$defs/SubmissionGroupStudentList"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "unread_message_count": {
      "default": 0,
      "title": "Unread Message Count",
      "type": "integer"
    }
  },
  "required": [
    "id",
    "path",
    "course_id",
    "course_content_type_id",
    "course_content_kind_id",
    "position",
    "course_content_type",
    "result_count",
    "submission_count",
    "color"
  ],
  "title": "CourseContentStudentList",
  "type": "object",
  "x-model-name": "CourseContentStudentList"
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

  validate(data: any): CourseContentStudentList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentStudentList', 'Expected an object');
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

    // Required field: path
    if (!('path' in data)) {
      errors.push('Missing required field: path');
    } else {
      if (typeof data.path !== 'string') {
        errors.push('Field path must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Required field: course_content_type_id
    if (!('course_content_type_id' in data)) {
      errors.push('Missing required field: course_content_type_id');
    } else {
      if (typeof data.course_content_type_id !== 'string') {
        errors.push('Field course_content_type_id must be a string');
      }
    }

    // Required field: course_content_kind_id
    if (!('course_content_kind_id' in data)) {
      errors.push('Missing required field: course_content_kind_id');
    } else {
      if (typeof data.course_content_kind_id !== 'string') {
        errors.push('Field course_content_kind_id must be a string');
      }
    }

    // Required field: position
    if (!('position' in data)) {
      errors.push('Missing required field: position');
    } else {
      if (typeof data.position !== 'number') {
        errors.push('Field position must be a number');
      }
    }

    // Optional field: max_group_size
    if ('max_group_size' in data && data.max_group_size !== undefined && data.max_group_size !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: submitted
    if ('submitted' in data && data.submitted !== undefined && data.submitted !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: course_content_type
    if (!('course_content_type' in data)) {
      errors.push('Missing required field: course_content_type');
    } else {
      // Reference field - basic object check
      if (typeof data.course_content_type !== 'object') {
        errors.push('Field course_content_type must be an object');
      }
    }

    // Required field: result_count
    if (!('result_count' in data)) {
      errors.push('Missing required field: result_count');
    } else {
      if (typeof data.result_count !== 'number') {
        errors.push('Field result_count must be a number');
      }
    }

    // Required field: submission_count
    if (!('submission_count' in data)) {
      errors.push('Missing required field: submission_count');
    } else {
      if (typeof data.submission_count !== 'number') {
        errors.push('Field submission_count must be a number');
      }
    }

    // Optional field: max_test_runs
    if ('max_test_runs' in data && data.max_test_runs !== undefined && data.max_test_runs !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: directory
    if ('directory' in data && data.directory !== undefined && data.directory !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: color
    if (!('color' in data)) {
      errors.push('Missing required field: color');
    } else {
      if (typeof data.color !== 'string') {
        errors.push('Field color must be a string');
      }
    }

    // Optional field: result
    if ('result' in data && data.result !== undefined && data.result !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: submission_group
    if ('submission_group' in data && data.submission_group !== undefined && data.submission_group !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: unread_message_count
    if ('unread_message_count' in data && data.unread_message_count !== undefined && data.unread_message_count !== null) {
      if (typeof data.unread_message_count !== 'number') {
        errors.push('Field unread_message_count must be a number');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentStudentList', errors.join('; '));
    }

    return data as CourseContentStudentList;
  }

  safeValidate(data: any): { success: true; data: CourseContentStudentList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentStudentList', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentStudentUpdate
 */
export class CourseContentStudentUpdateValidator extends BaseValidator<CourseContentStudentUpdate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "status": {
      "anyOf": [
        {
          "enum": [
            "corrected",
            "correction_necessary",
            "improvement_possible",
            "not_reviewed"
          ],
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Status"
    },
    "grading": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Grading"
    },
    "feedback": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Feedback"
    }
  },
  "title": "CourseContentStudentUpdate",
  "type": "object",
  "x-model-name": "CourseContentStudentUpdate"
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

  validate(data: any): CourseContentStudentUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentStudentUpdate', 'Expected an object');
    }

    // Optional field: status
    if ('status' in data && data.status !== undefined && data.status !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: grading
    if ('grading' in data && data.grading !== undefined && data.grading !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: feedback
    if ('feedback' in data && data.feedback !== undefined && data.feedback !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentStudentUpdate', errors.join('; '));
    }

    return data as CourseContentStudentUpdate;
  }

  safeValidate(data: any): { success: true; data: CourseContentStudentUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentStudentUpdate', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentStudentQuery
 */
export class CourseContentStudentQueryValidator extends BaseValidator<CourseContentStudentQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    },
    "course_content_type_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Content Type Id"
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
    "project": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Project"
    },
    "provider_url": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Provider Url"
    },
    "nlevel": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Nlevel"
    },
    "descendants": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Descendants"
    },
    "ascendants": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Ascendants"
    }
  },
  "title": "CourseContentStudentQuery",
  "type": "object",
  "x-model-name": "CourseContentStudentQuery"
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

  validate(data: any): CourseContentStudentQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentStudentQuery', 'Expected an object');
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

    // Optional field: path
    if ('path' in data && data.path !== undefined && data.path !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_id
    if ('course_id' in data && data.course_id !== undefined && data.course_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_content_type_id
    if ('course_content_type_id' in data && data.course_content_type_id !== undefined && data.course_content_type_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: directory
    if ('directory' in data && data.directory !== undefined && data.directory !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: project
    if ('project' in data && data.project !== undefined && data.project !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: provider_url
    if ('provider_url' in data && data.provider_url !== undefined && data.provider_url !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: nlevel
    if ('nlevel' in data && data.nlevel !== undefined && data.nlevel !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: descendants
    if ('descendants' in data && data.descendants !== undefined && data.descendants !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: ascendants
    if ('ascendants' in data && data.ascendants !== undefined && data.ascendants !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentStudentQuery', errors.join('; '));
    }

    return data as CourseContentStudentQuery;
  }

  safeValidate(data: any): { success: true; data: CourseContentStudentQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentStudentQuery', String(error)) };
    }
  }
}

/**
 * Validator for CourseStudentRepository
 */
export class CourseStudentRepositoryValidator extends BaseValidator<CourseStudentRepository> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "provider_url": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Provider Url"
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
    }
  },
  "title": "CourseStudentRepository",
  "type": "object",
  "x-model-name": "CourseStudentRepository"
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

  validate(data: any): CourseStudentRepository {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseStudentRepository', 'Expected an object');
    }

    // Optional field: provider_url
    if ('provider_url' in data && data.provider_url !== undefined && data.provider_url !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: full_path
    if ('full_path' in data && data.full_path !== undefined && data.full_path !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseStudentRepository', errors.join('; '));
    }

    return data as CourseStudentRepository;
  }

  safeValidate(data: any): { success: true; data: CourseStudentRepository } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseStudentRepository', String(error)) };
    }
  }
}

/**
 * Validator for CourseStudentGet
 */
export class CourseStudentGetValidator extends BaseValidator<CourseStudentGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseContentKindGet": {
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
        "has_ascendants": {
          "title": "Has Ascendants",
          "type": "boolean"
        },
        "has_descendants": {
          "title": "Has Descendants",
          "type": "boolean"
        },
        "submittable": {
          "title": "Submittable",
          "type": "boolean"
        },
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
        }
      },
      "required": [
        "has_ascendants",
        "has_descendants",
        "submittable",
        "id"
      ],
      "title": "CourseContentKindGet",
      "type": "object"
    },
    "CourseContentTypeGet": {
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
        "slug": {
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
        "color": {
          "title": "Color",
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
        },
        "course_id": {
          "title": "Course Id",
          "type": "string"
        },
        "course_content_kind_id": {
          "title": "Course Content Kind Id",
          "type": "string"
        },
        "course_content_kind": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseContentKindGet"
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
        "slug",
        "color",
        "course_id",
        "course_content_kind_id"
      ],
      "title": "CourseContentTypeGet",
      "type": "object"
    },
    "CourseStudentRepository": {
      "properties": {
        "provider_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Provider Url"
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
        }
      },
      "title": "CourseStudentRepository",
      "type": "object"
    }
  },
  "properties": {
    "id": {
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
      "title": "Title"
    },
    "course_family_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Family Id"
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
    "course_content_types": {
      "items": {
        "$ref": "#/$defs/CourseContentTypeGet"
      },
      "title": "Course Content Types",
      "type": "array"
    },
    "path": {
      "title": "Path",
      "type": "string"
    },
    "repository": {
      "$ref": "#/$defs/CourseStudentRepository"
    }
  },
  "required": [
    "id",
    "course_content_types",
    "path",
    "repository"
  ],
  "title": "CourseStudentGet",
  "type": "object",
  "x-model-name": "CourseStudentGet"
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

  validate(data: any): CourseStudentGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseStudentGet', 'Expected an object');
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

    // Optional field: course_family_id
    if ('course_family_id' in data && data.course_family_id !== undefined && data.course_family_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: organization_id
    if ('organization_id' in data && data.organization_id !== undefined && data.organization_id !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: course_content_types
    if (!('course_content_types' in data)) {
      errors.push('Missing required field: course_content_types');
    } else {
      if (!Array.isArray(data.course_content_types)) {
        errors.push('Field course_content_types must be an array');
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

    // Required field: repository
    if (!('repository' in data)) {
      errors.push('Missing required field: repository');
    } else {
      // Reference field - basic object check
      if (typeof data.repository !== 'object') {
        errors.push('Field repository must be an object');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseStudentGet', errors.join('; '));
    }

    return data as CourseStudentGet;
  }

  safeValidate(data: any): { success: true; data: CourseStudentGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseStudentGet', String(error)) };
    }
  }
}

/**
 * Validator for CourseStudentList
 */
export class CourseStudentListValidator extends BaseValidator<CourseStudentList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseStudentRepository": {
      "properties": {
        "provider_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Provider Url"
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
        }
      },
      "title": "CourseStudentRepository",
      "type": "object"
    }
  },
  "properties": {
    "id": {
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
      "title": "Title"
    },
    "course_family_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Family Id"
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
    "path": {
      "title": "Path",
      "type": "string"
    },
    "repository": {
      "$ref": "#/$defs/CourseStudentRepository"
    }
  },
  "required": [
    "id",
    "path",
    "repository"
  ],
  "title": "CourseStudentList",
  "type": "object",
  "x-model-name": "CourseStudentList"
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

  validate(data: any): CourseStudentList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseStudentList', 'Expected an object');
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

    // Optional field: course_family_id
    if ('course_family_id' in data && data.course_family_id !== undefined && data.course_family_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: organization_id
    if ('organization_id' in data && data.organization_id !== undefined && data.organization_id !== null) {
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

    // Required field: repository
    if (!('repository' in data)) {
      errors.push('Missing required field: repository');
    } else {
      // Reference field - basic object check
      if (typeof data.repository !== 'object') {
        errors.push('Field repository must be an object');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseStudentList', errors.join('; '));
    }

    return data as CourseStudentList;
  }

  safeValidate(data: any): { success: true; data: CourseStudentList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseStudentList', String(error)) };
    }
  }
}

/**
 * Validator for CourseStudentQuery
 */
export class CourseStudentQueryValidator extends BaseValidator<CourseStudentQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    "course_family_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Family Id"
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
    "provider_url": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Provider Url"
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
    "full_path_student": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Full Path Student"
    }
  },
  "title": "CourseStudentQuery",
  "type": "object",
  "x-model-name": "CourseStudentQuery"
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

  validate(data: any): CourseStudentQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseStudentQuery', 'Expected an object');
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

    // Optional field: course_family_id
    if ('course_family_id' in data && data.course_family_id !== undefined && data.course_family_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: organization_id
    if ('organization_id' in data && data.organization_id !== undefined && data.organization_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: provider_url
    if ('provider_url' in data && data.provider_url !== undefined && data.provider_url !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: full_path
    if ('full_path' in data && data.full_path !== undefined && data.full_path !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: full_path_student
    if ('full_path_student' in data && data.full_path_student !== undefined && data.full_path_student !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseStudentQuery', errors.join('; '));
    }

    return data as CourseStudentQuery;
  }

  safeValidate(data: any): { success: true; data: CourseStudentQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseStudentQuery', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentKindCreate
 */
export class CourseContentKindCreateValidator extends BaseValidator<CourseContentKindCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    "has_ascendants": {
      "title": "Has Ascendants",
      "type": "boolean"
    },
    "has_descendants": {
      "title": "Has Descendants",
      "type": "boolean"
    },
    "submittable": {
      "title": "Submittable",
      "type": "boolean"
    }
  },
  "required": [
    "has_ascendants",
    "has_descendants",
    "submittable"
  ],
  "title": "CourseContentKindCreate",
  "type": "object",
  "x-model-name": "CourseContentKindCreate"
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

  validate(data: any): CourseContentKindCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentKindCreate', 'Expected an object');
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: has_ascendants
    if (!('has_ascendants' in data)) {
      errors.push('Missing required field: has_ascendants');
    } else {
      if (typeof data.has_ascendants !== 'boolean') {
        errors.push('Field has_ascendants must be a boolean');
      }
    }

    // Required field: has_descendants
    if (!('has_descendants' in data)) {
      errors.push('Missing required field: has_descendants');
    } else {
      if (typeof data.has_descendants !== 'boolean') {
        errors.push('Field has_descendants must be a boolean');
      }
    }

    // Required field: submittable
    if (!('submittable' in data)) {
      errors.push('Missing required field: submittable');
    } else {
      if (typeof data.submittable !== 'boolean') {
        errors.push('Field submittable must be a boolean');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentKindCreate', errors.join('; '));
    }

    return data as CourseContentKindCreate;
  }

  safeValidate(data: any): { success: true; data: CourseContentKindCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentKindCreate', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentKindGet
 */
export class CourseContentKindGetValidator extends BaseValidator<CourseContentKindGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    "has_ascendants": {
      "title": "Has Ascendants",
      "type": "boolean"
    },
    "has_descendants": {
      "title": "Has Descendants",
      "type": "boolean"
    },
    "submittable": {
      "title": "Submittable",
      "type": "boolean"
    },
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
    }
  },
  "required": [
    "has_ascendants",
    "has_descendants",
    "submittable",
    "id"
  ],
  "title": "CourseContentKindGet",
  "type": "object",
  "x-model-name": "CourseContentKindGet"
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

  validate(data: any): CourseContentKindGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentKindGet', 'Expected an object');
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: has_ascendants
    if (!('has_ascendants' in data)) {
      errors.push('Missing required field: has_ascendants');
    } else {
      if (typeof data.has_ascendants !== 'boolean') {
        errors.push('Field has_ascendants must be a boolean');
      }
    }

    // Required field: has_descendants
    if (!('has_descendants' in data)) {
      errors.push('Missing required field: has_descendants');
    } else {
      if (typeof data.has_descendants !== 'boolean') {
        errors.push('Field has_descendants must be a boolean');
      }
    }

    // Required field: submittable
    if (!('submittable' in data)) {
      errors.push('Missing required field: submittable');
    } else {
      if (typeof data.submittable !== 'boolean') {
        errors.push('Field submittable must be a boolean');
      }
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

    if (errors.length > 0) {
      throw new ValidationError('CourseContentKindGet', errors.join('; '));
    }

    return data as CourseContentKindGet;
  }

  safeValidate(data: any): { success: true; data: CourseContentKindGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentKindGet', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentKindList
 */
export class CourseContentKindListValidator extends BaseValidator<CourseContentKindList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "id": {
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
      "title": "Title"
    },
    "has_ascendants": {
      "title": "Has Ascendants",
      "type": "boolean"
    },
    "has_descendants": {
      "title": "Has Descendants",
      "type": "boolean"
    },
    "submittable": {
      "title": "Submittable",
      "type": "boolean"
    }
  },
  "required": [
    "id",
    "has_ascendants",
    "has_descendants",
    "submittable"
  ],
  "title": "CourseContentKindList",
  "type": "object",
  "x-model-name": "CourseContentKindList"
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

  validate(data: any): CourseContentKindList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentKindList', 'Expected an object');
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

    // Required field: has_ascendants
    if (!('has_ascendants' in data)) {
      errors.push('Missing required field: has_ascendants');
    } else {
      if (typeof data.has_ascendants !== 'boolean') {
        errors.push('Field has_ascendants must be a boolean');
      }
    }

    // Required field: has_descendants
    if (!('has_descendants' in data)) {
      errors.push('Missing required field: has_descendants');
    } else {
      if (typeof data.has_descendants !== 'boolean') {
        errors.push('Field has_descendants must be a boolean');
      }
    }

    // Required field: submittable
    if (!('submittable' in data)) {
      errors.push('Missing required field: submittable');
    } else {
      if (typeof data.submittable !== 'boolean') {
        errors.push('Field submittable must be a boolean');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentKindList', errors.join('; '));
    }

    return data as CourseContentKindList;
  }

  safeValidate(data: any): { success: true; data: CourseContentKindList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentKindList', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentKindUpdate
 */
export class CourseContentKindUpdateValidator extends BaseValidator<CourseContentKindUpdate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    }
  },
  "title": "CourseContentKindUpdate",
  "type": "object",
  "x-model-name": "CourseContentKindUpdate"
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

  validate(data: any): CourseContentKindUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentKindUpdate', 'Expected an object');
    }

    // Optional field: title
    if ('title' in data && data.title !== undefined && data.title !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: description
    if ('description' in data && data.description !== undefined && data.description !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentKindUpdate', errors.join('; '));
    }

    return data as CourseContentKindUpdate;
  }

  safeValidate(data: any): { success: true; data: CourseContentKindUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentKindUpdate', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentKindQuery
 */
export class CourseContentKindQueryValidator extends BaseValidator<CourseContentKindQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    "has_ascendants": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Has Ascendants"
    },
    "has_descendants": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Has Descendants"
    },
    "submittable": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Submittable"
    }
  },
  "title": "CourseContentKindQuery",
  "type": "object",
  "x-model-name": "CourseContentKindQuery"
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

  validate(data: any): CourseContentKindQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentKindQuery', 'Expected an object');
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

    // Optional field: has_ascendants
    if ('has_ascendants' in data && data.has_ascendants !== undefined && data.has_ascendants !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: has_descendants
    if ('has_descendants' in data && data.has_descendants !== undefined && data.has_descendants !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: submittable
    if ('submittable' in data && data.submittable !== undefined && data.submittable !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentKindQuery', errors.join('; '));
    }

    return data as CourseContentKindQuery;
  }

  safeValidate(data: any): { success: true; data: CourseContentKindQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentKindQuery', String(error)) };
    }
  }
}

/**
 * DTO for releasing a course.
 */
export class ReleaseCourseCreateValidator extends BaseValidator<ReleaseCourseCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "ComputorDeploymentConfig": {
      "properties": {
        "organization": {
          "$ref": "#/$defs/OrganizationConfig"
        },
        "courseFamily": {
          "$ref": "#/$defs/CourseFamilyConfig"
        },
        "course": {
          "$ref": "#/$defs/CourseConfig"
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
          "default": null,
          "title": "Settings"
        }
      },
      "required": [
        "organization",
        "courseFamily",
        "course"
      ],
      "title": "ComputorDeploymentConfig",
      "type": "object"
    },
    "CourseConfig": {
      "properties": {
        "name": {
          "title": "Name",
          "type": "string"
        },
        "path": {
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
          "title": "Description"
        },
        "executionBackends": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/CourseExecutionBackendConfig"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Executionbackends"
        },
        "settings": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseSettingsConfig"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "required": [
        "name",
        "path"
      ],
      "title": "CourseConfig",
      "type": "object"
    },
    "CourseExecutionBackendConfig": {
      "properties": {
        "slug": {
          "title": "Slug",
          "type": "string"
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
          "default": null,
          "title": "Settings"
        }
      },
      "required": [
        "slug"
      ],
      "title": "CourseExecutionBackendConfig",
      "type": "object"
    },
    "CourseFamilyConfig": {
      "properties": {
        "name": {
          "title": "Name",
          "type": "string"
        },
        "path": {
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
          "default": null,
          "title": "Settings"
        }
      },
      "required": [
        "name",
        "path"
      ],
      "title": "CourseFamilyConfig",
      "type": "object"
    },
    "CourseSettingsConfig": {
      "additionalProperties": true,
      "properties": {
        "source": {
          "anyOf": [
            {
              "$ref": "#/$defs/FileSourceConfig"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "CourseSettingsConfig",
      "type": "object"
    },
    "FileSourceConfig": {
      "properties": {
        "url": {
          "title": "Url",
          "type": "string"
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
      "required": [
        "url"
      ],
      "title": "FileSourceConfig",
      "type": "object"
    },
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
    "OrganizationConfig": {
      "properties": {
        "name": {
          "title": "Name",
          "type": "string"
        },
        "path": {
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
          "default": null,
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
          "default": null
        }
      },
      "required": [
        "name",
        "path"
      ],
      "title": "OrganizationConfig",
      "type": "object"
    }
  },
  "description": "DTO for releasing a course.",
  "properties": {
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
    },
    "gitlab_url": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Gitlab Url"
    },
    "descendants": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": false,
      "title": "Descendants"
    },
    "deployment": {
      "anyOf": [
        {
          "$ref": "#/$defs/ComputorDeploymentConfig"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "title": "ReleaseCourseCreate",
  "type": "object",
  "x-model-name": "ReleaseCourseCreate"
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

  validate(data: any): ReleaseCourseCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ReleaseCourseCreate', 'Expected an object');
    }

    // Optional field: course_id
    if ('course_id' in data && data.course_id !== undefined && data.course_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: gitlab_url
    if ('gitlab_url' in data && data.gitlab_url !== undefined && data.gitlab_url !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: descendants
    if ('descendants' in data && data.descendants !== undefined && data.descendants !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: deployment
    if ('deployment' in data && data.deployment !== undefined && data.deployment !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ReleaseCourseCreate', errors.join('; '));
    }

    return data as ReleaseCourseCreate;
  }

  safeValidate(data: any): { success: true; data: ReleaseCourseCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ReleaseCourseCreate', String(error)) };
    }
  }
}

/**
 * DTO for releasing course content.
 */
export class ReleaseCourseContentCreateValidator extends BaseValidator<ReleaseCourseContentCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "ComputorDeploymentConfig": {
      "properties": {
        "organization": {
          "$ref": "#/$defs/OrganizationConfig"
        },
        "courseFamily": {
          "$ref": "#/$defs/CourseFamilyConfig"
        },
        "course": {
          "$ref": "#/$defs/CourseConfig"
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
          "default": null,
          "title": "Settings"
        }
      },
      "required": [
        "organization",
        "courseFamily",
        "course"
      ],
      "title": "ComputorDeploymentConfig",
      "type": "object"
    },
    "CourseConfig": {
      "properties": {
        "name": {
          "title": "Name",
          "type": "string"
        },
        "path": {
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
          "title": "Description"
        },
        "executionBackends": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/CourseExecutionBackendConfig"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Executionbackends"
        },
        "settings": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseSettingsConfig"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "required": [
        "name",
        "path"
      ],
      "title": "CourseConfig",
      "type": "object"
    },
    "CourseExecutionBackendConfig": {
      "properties": {
        "slug": {
          "title": "Slug",
          "type": "string"
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
          "default": null,
          "title": "Settings"
        }
      },
      "required": [
        "slug"
      ],
      "title": "CourseExecutionBackendConfig",
      "type": "object"
    },
    "CourseFamilyConfig": {
      "properties": {
        "name": {
          "title": "Name",
          "type": "string"
        },
        "path": {
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
          "default": null,
          "title": "Settings"
        }
      },
      "required": [
        "name",
        "path"
      ],
      "title": "CourseFamilyConfig",
      "type": "object"
    },
    "CourseSettingsConfig": {
      "additionalProperties": true,
      "properties": {
        "source": {
          "anyOf": [
            {
              "$ref": "#/$defs/FileSourceConfig"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "CourseSettingsConfig",
      "type": "object"
    },
    "FileSourceConfig": {
      "properties": {
        "url": {
          "title": "Url",
          "type": "string"
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
      "required": [
        "url"
      ],
      "title": "FileSourceConfig",
      "type": "object"
    },
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
    "OrganizationConfig": {
      "properties": {
        "name": {
          "title": "Name",
          "type": "string"
        },
        "path": {
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
          "default": null,
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
          "default": null
        }
      },
      "required": [
        "name",
        "path"
      ],
      "title": "OrganizationConfig",
      "type": "object"
    }
  },
  "description": "DTO for releasing course content.",
  "properties": {
    "release_dir": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Release Dir"
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
    },
    "gitlab_url": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Gitlab Url"
    },
    "ascendants": {
      "default": false,
      "title": "Ascendants",
      "type": "boolean"
    },
    "descendants": {
      "default": false,
      "title": "Descendants",
      "type": "boolean"
    },
    "deployment": {
      "anyOf": [
        {
          "$ref": "#/$defs/ComputorDeploymentConfig"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "title": "ReleaseCourseContentCreate",
  "type": "object",
  "x-model-name": "ReleaseCourseContentCreate"
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

  validate(data: any): ReleaseCourseContentCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('ReleaseCourseContentCreate', 'Expected an object');
    }

    // Optional field: release_dir
    if ('release_dir' in data && data.release_dir !== undefined && data.release_dir !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_id
    if ('course_id' in data && data.course_id !== undefined && data.course_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: gitlab_url
    if ('gitlab_url' in data && data.gitlab_url !== undefined && data.gitlab_url !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: ascendants
    if ('ascendants' in data && data.ascendants !== undefined && data.ascendants !== null) {
      if (typeof data.ascendants !== 'boolean') {
        errors.push('Field ascendants must be a boolean');
      }
    }

    // Optional field: descendants
    if ('descendants' in data && data.descendants !== undefined && data.descendants !== null) {
      if (typeof data.descendants !== 'boolean') {
        errors.push('Field descendants must be a boolean');
      }
    }

    // Optional field: deployment
    if ('deployment' in data && data.deployment !== undefined && data.deployment !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('ReleaseCourseContentCreate', errors.join('; '));
    }

    return data as ReleaseCourseContentCreate;
  }

  safeValidate(data: any): { success: true; data: ReleaseCourseContentCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('ReleaseCourseContentCreate', String(error)) };
    }
  }
}

/**
 * DTO for updating course release.
 */
export class CourseReleaseUpdateValidator extends BaseValidator<CourseReleaseUpdate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseContentTypeCreate": {
      "properties": {
        "slug": {
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
          "default": null,
          "title": "Properties"
        },
        "course_id": {
          "title": "Course Id",
          "type": "string"
        },
        "course_content_kind_id": {
          "title": "Course Content Kind Id",
          "type": "string"
        }
      },
      "required": [
        "slug",
        "course_id",
        "course_content_kind_id"
      ],
      "title": "CourseContentTypeCreate",
      "type": "object"
    },
    "CourseProperties": {
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
      "title": "CourseProperties",
      "type": "object"
    },
    "CourseUpdate": {
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
        "language_code": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Language Code"
        },
        "properties": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseProperties"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "CourseUpdate",
      "type": "object"
    },
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
  "description": "DTO for updating course release.",
  "properties": {
    "course": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseUpdate"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "course_content_types": {
      "items": {
        "$ref": "#/$defs/CourseContentTypeCreate"
      },
      "title": "Course Content Types",
      "type": "array"
    }
  },
  "required": [
    "course_content_types"
  ],
  "title": "CourseReleaseUpdate",
  "type": "object",
  "x-model-name": "CourseReleaseUpdate"
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

  validate(data: any): CourseReleaseUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseReleaseUpdate', 'Expected an object');
    }

    // Optional field: course
    if ('course' in data && data.course !== undefined && data.course !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: course_content_types
    if (!('course_content_types' in data)) {
      errors.push('Missing required field: course_content_types');
    } else {
      if (!Array.isArray(data.course_content_types)) {
        errors.push('Field course_content_types must be an array');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseReleaseUpdate', errors.join('; '));
    }

    return data as CourseReleaseUpdate;
  }

  safeValidate(data: any): { success: true; data: CourseReleaseUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseReleaseUpdate', String(error)) };
    }
  }
}

/**
 * Request to create a course family via Temporal workflow.
 */
export class CourseFamilyTaskRequestValidator extends BaseValidator<CourseFamilyTaskRequest> {
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
  "description": "Request to create a course family via Temporal workflow.",
  "properties": {
    "course_family": {
      "additionalProperties": true,
      "title": "Course Family",
      "type": "object"
    },
    "organization_id": {
      "title": "Organization Id",
      "type": "string"
    },
    "gitlab": {
      "anyOf": [
        {
          "$ref": "#/$defs/GitLabCredentials"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "required": [
    "course_family",
    "organization_id"
  ],
  "title": "CourseFamilyTaskRequest",
  "type": "object",
  "x-model-name": "CourseFamilyTaskRequest"
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

  validate(data: any): CourseFamilyTaskRequest {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseFamilyTaskRequest', 'Expected an object');
    }

    // Required field: course_family
    if (!('course_family' in data)) {
      errors.push('Missing required field: course_family');
    } else {
      if (typeof data.course_family !== 'object' || data.course_family === null) {
        errors.push('Field course_family must be an object');
      }
    }

    // Required field: organization_id
    if (!('organization_id' in data)) {
      errors.push('Missing required field: organization_id');
    } else {
      if (typeof data.organization_id !== 'string') {
        errors.push('Field organization_id must be a string');
      }
    }

    // Optional field: gitlab
    if ('gitlab' in data && data.gitlab !== undefined && data.gitlab !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseFamilyTaskRequest', errors.join('; '));
    }

    return data as CourseFamilyTaskRequest;
  }

  safeValidate(data: any): { success: true; data: CourseFamilyTaskRequest } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseFamilyTaskRequest', String(error)) };
    }
  }
}

/**
 * Request to create a course via Temporal workflow.
 */
export class CourseTaskRequestValidator extends BaseValidator<CourseTaskRequest> {
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
  "description": "Request to create a course via Temporal workflow.",
  "properties": {
    "course": {
      "additionalProperties": true,
      "title": "Course",
      "type": "object"
    },
    "course_family_id": {
      "title": "Course Family Id",
      "type": "string"
    },
    "gitlab": {
      "anyOf": [
        {
          "$ref": "#/$defs/GitLabCredentials"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "required": [
    "course",
    "course_family_id"
  ],
  "title": "CourseTaskRequest",
  "type": "object",
  "x-model-name": "CourseTaskRequest"
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

  validate(data: any): CourseTaskRequest {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseTaskRequest', 'Expected an object');
    }

    // Required field: course
    if (!('course' in data)) {
      errors.push('Missing required field: course');
    } else {
      if (typeof data.course !== 'object' || data.course === null) {
        errors.push('Field course must be an object');
      }
    }

    // Required field: course_family_id
    if (!('course_family_id' in data)) {
      errors.push('Missing required field: course_family_id');
    } else {
      if (typeof data.course_family_id !== 'string') {
        errors.push('Field course_family_id must be a string');
      }
    }

    // Optional field: gitlab
    if ('gitlab' in data && data.gitlab !== undefined && data.gitlab !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseTaskRequest', errors.join('; '));
    }

    return data as CourseTaskRequest;
  }

  safeValidate(data: any): { success: true; data: CourseTaskRequest } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseTaskRequest', String(error)) };
    }
  }
}

/**
 * Configuration for course execution backend.
 */
export class CourseExecutionBackendConfigValidator extends BaseValidator<CourseExecutionBackendConfig> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Configuration for course execution backend.",
  "properties": {
    "slug": {
      "description": "Unique identifier for the execution backend",
      "title": "Slug",
      "type": "string"
    },
    "version": {
      "description": "Version of the execution backend (e.g., 'r2024b', 'v1.0')",
      "title": "Version",
      "type": "string"
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
      "default": null,
      "description": "Backend-specific settings",
      "title": "Settings"
    }
  },
  "required": [
    "slug",
    "version"
  ],
  "title": "CourseExecutionBackendConfig",
  "type": "object",
  "x-model-name": "CourseExecutionBackendConfig"
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

  validate(data: any): CourseExecutionBackendConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseExecutionBackendConfig', 'Expected an object');
    }

    // Required field: slug
    if (!('slug' in data)) {
      errors.push('Missing required field: slug');
    } else {
      if (typeof data.slug !== 'string') {
        errors.push('Field slug must be a string');
      }
    }

    // Required field: version
    if (!('version' in data)) {
      errors.push('Missing required field: version');
    } else {
      if (typeof data.version !== 'string') {
        errors.push('Field version must be a string');
      }
    }

    // Optional field: settings
    if ('settings' in data && data.settings !== undefined && data.settings !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseExecutionBackendConfig', errors.join('; '));
    }

    return data as CourseExecutionBackendConfig;
  }

  safeValidate(data: any): { success: true; data: CourseExecutionBackendConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseExecutionBackendConfig', String(error)) };
    }
  }
}

/**
 * Validator for CourseFamilyProperties
 */
export class CourseFamilyPropertiesValidator extends BaseValidator<CourseFamilyProperties> {
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
  "title": "CourseFamilyProperties",
  "type": "object",
  "x-model-name": "CourseFamilyProperties"
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

  validate(data: any): CourseFamilyProperties {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseFamilyProperties', 'Expected an object');
    }

    // Optional field: gitlab
    if ('gitlab' in data && data.gitlab !== undefined && data.gitlab !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseFamilyProperties', errors.join('; '));
    }

    return data as CourseFamilyProperties;
  }

  safeValidate(data: any): { success: true; data: CourseFamilyProperties } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseFamilyProperties', String(error)) };
    }
  }
}

/**
 * Validator for CourseFamilyPropertiesGet
 */
export class CourseFamilyPropertiesGetValidator extends BaseValidator<CourseFamilyPropertiesGet> {
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
  "title": "CourseFamilyPropertiesGet",
  "type": "object",
  "x-model-name": "CourseFamilyPropertiesGet"
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

  validate(data: any): CourseFamilyPropertiesGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseFamilyPropertiesGet', 'Expected an object');
    }

    // Optional field: gitlab
    if ('gitlab' in data && data.gitlab !== undefined && data.gitlab !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseFamilyPropertiesGet', errors.join('; '));
    }

    return data as CourseFamilyPropertiesGet;
  }

  safeValidate(data: any): { success: true; data: CourseFamilyPropertiesGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseFamilyPropertiesGet', String(error)) };
    }
  }
}

/**
 * Validator for CourseFamilyCreate
 */
export class CourseFamilyCreateValidator extends BaseValidator<CourseFamilyCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseFamilyProperties": {
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
      "title": "CourseFamilyProperties",
      "type": "object"
    },
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
      "title": "Path",
      "type": "string"
    },
    "organization_id": {
      "title": "Organization Id",
      "type": "string"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseFamilyProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "required": [
    "path",
    "organization_id"
  ],
  "title": "CourseFamilyCreate",
  "type": "object",
  "x-model-name": "CourseFamilyCreate"
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

  validate(data: any): CourseFamilyCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseFamilyCreate', 'Expected an object');
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

    // Required field: organization_id
    if (!('organization_id' in data)) {
      errors.push('Missing required field: organization_id');
    } else {
      if (typeof data.organization_id !== 'string') {
        errors.push('Field organization_id must be a string');
      }
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseFamilyCreate', errors.join('; '));
    }

    return data as CourseFamilyCreate;
  }

  safeValidate(data: any): { success: true; data: CourseFamilyCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseFamilyCreate', String(error)) };
    }
  }
}

/**
 * Validator for CourseFamilyGet
 */
export class CourseFamilyGetValidator extends BaseValidator<CourseFamilyGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseFamilyPropertiesGet": {
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
      "title": "CourseFamilyPropertiesGet",
      "type": "object"
    },
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
    "OrganizationGet": {
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
      "title": "Path",
      "type": "string"
    },
    "organization_id": {
      "title": "Organization Id",
      "type": "string"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseFamilyPropertiesGet"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "organization": {
      "anyOf": [
        {
          "$ref": "#/$defs/OrganizationGet"
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
    "path",
    "organization_id"
  ],
  "title": "CourseFamilyGet",
  "type": "object",
  "x-model-name": "CourseFamilyGet"
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

  validate(data: any): CourseFamilyGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseFamilyGet', 'Expected an object');
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

    // Required field: organization_id
    if (!('organization_id' in data)) {
      errors.push('Missing required field: organization_id');
    } else {
      if (typeof data.organization_id !== 'string') {
        errors.push('Field organization_id must be a string');
      }
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: organization
    if ('organization' in data && data.organization !== undefined && data.organization !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseFamilyGet', errors.join('; '));
    }

    return data as CourseFamilyGet;
  }

  safeValidate(data: any): { success: true; data: CourseFamilyGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseFamilyGet', String(error)) };
    }
  }
}

/**
 * Validator for CourseFamilyList
 */
export class CourseFamilyListValidator extends BaseValidator<CourseFamilyList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "id": {
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
      "title": "Title"
    },
    "organization_id": {
      "title": "Organization Id",
      "type": "string"
    },
    "path": {
      "title": "Path",
      "type": "string"
    }
  },
  "required": [
    "id",
    "organization_id",
    "path"
  ],
  "title": "CourseFamilyList",
  "type": "object",
  "x-model-name": "CourseFamilyList"
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

  validate(data: any): CourseFamilyList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseFamilyList', 'Expected an object');
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

    // Required field: organization_id
    if (!('organization_id' in data)) {
      errors.push('Missing required field: organization_id');
    } else {
      if (typeof data.organization_id !== 'string') {
        errors.push('Field organization_id must be a string');
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
      throw new ValidationError('CourseFamilyList', errors.join('; '));
    }

    return data as CourseFamilyList;
  }

  safeValidate(data: any): { success: true; data: CourseFamilyList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseFamilyList', String(error)) };
    }
  }
}

/**
 * Validator for CourseFamilyUpdate
 */
export class CourseFamilyUpdateValidator extends BaseValidator<CourseFamilyUpdate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseFamilyProperties": {
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
      "title": "CourseFamilyProperties",
      "type": "object"
    },
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
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseFamilyProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "title": "CourseFamilyUpdate",
  "type": "object",
  "x-model-name": "CourseFamilyUpdate"
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

  validate(data: any): CourseFamilyUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseFamilyUpdate', 'Expected an object');
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

    // Optional field: organization_id
    if ('organization_id' in data && data.organization_id !== undefined && data.organization_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseFamilyUpdate', errors.join('; '));
    }

    return data as CourseFamilyUpdate;
  }

  safeValidate(data: any): { success: true; data: CourseFamilyUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseFamilyUpdate', String(error)) };
    }
  }
}

/**
 * Validator for CourseFamilyQuery
 */
export class CourseFamilyQueryValidator extends BaseValidator<CourseFamilyQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    "properties": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Properties"
    }
  },
  "title": "CourseFamilyQuery",
  "type": "object",
  "x-model-name": "CourseFamilyQuery"
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

  validate(data: any): CourseFamilyQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseFamilyQuery', 'Expected an object');
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

    // Optional field: organization_id
    if ('organization_id' in data && data.organization_id !== undefined && data.organization_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseFamilyQuery', errors.join('; '));
    }

    return data as CourseFamilyQuery;
  }

  safeValidate(data: any): { success: true; data: CourseFamilyQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseFamilyQuery', String(error)) };
    }
  }
}

/**
 * Properties for course content (stored in JSONB).
 */
export class CourseContentPropertiesValidator extends BaseValidator<CourseContentProperties> {
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
  "description": "Properties for course content (stored in JSONB).",
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
  "title": "CourseContentProperties",
  "type": "object",
  "x-model-name": "CourseContentProperties"
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

  validate(data: any): CourseContentProperties {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentProperties', 'Expected an object');
    }

    // Optional field: gitlab
    if ('gitlab' in data && data.gitlab !== undefined && data.gitlab !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentProperties', errors.join('; '));
    }

    return data as CourseContentProperties;
  }

  safeValidate(data: any): { success: true; data: CourseContentProperties } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentProperties', String(error)) };
    }
  }
}

/**
 * Properties for course content GET responses.
 */
export class CourseContentPropertiesGetValidator extends BaseValidator<CourseContentPropertiesGet> {
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
  "description": "Properties for course content GET responses.",
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
  "title": "CourseContentPropertiesGet",
  "type": "object",
  "x-model-name": "CourseContentPropertiesGet"
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

  validate(data: any): CourseContentPropertiesGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentPropertiesGet', 'Expected an object');
    }

    // Optional field: gitlab
    if ('gitlab' in data && data.gitlab !== undefined && data.gitlab !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentPropertiesGet', errors.join('; '));
    }

    return data as CourseContentPropertiesGet;
  }

  safeValidate(data: any): { success: true; data: CourseContentPropertiesGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentPropertiesGet', String(error)) };
    }
  }
}

/**
 * DTO for creating course content.
 */
export class CourseContentCreateValidator extends BaseValidator<CourseContentCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseContentProperties": {
      "additionalProperties": true,
      "description": "Properties for course content (stored in JSONB).",
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
      "title": "CourseContentProperties",
      "type": "object"
    },
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
  "description": "DTO for creating course content.",
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
      "title": "Path",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
    },
    "course_content_type_id": {
      "title": "Course Content Type Id",
      "type": "string"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseContentProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "position": {
      "default": 0,
      "title": "Position",
      "type": "number"
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
      "title": "Max Submissions"
    },
    "execution_backend_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Execution Backend Id"
    }
  },
  "required": [
    "path",
    "course_id",
    "course_content_type_id"
  ],
  "title": "CourseContentCreate",
  "type": "object",
  "x-model-name": "CourseContentCreate"
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

  validate(data: any): CourseContentCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentCreate', 'Expected an object');
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

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Required field: course_content_type_id
    if (!('course_content_type_id' in data)) {
      errors.push('Missing required field: course_content_type_id');
    } else {
      if (typeof data.course_content_type_id !== 'string') {
        errors.push('Field course_content_type_id must be a string');
      }
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: position
    if ('position' in data && data.position !== undefined && data.position !== null) {
      if (typeof data.position !== 'number') {
        errors.push('Field position must be a number');
      }
    }

    // Optional field: max_group_size
    if ('max_group_size' in data && data.max_group_size !== undefined && data.max_group_size !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_test_runs
    if ('max_test_runs' in data && data.max_test_runs !== undefined && data.max_test_runs !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_submissions
    if ('max_submissions' in data && data.max_submissions !== undefined && data.max_submissions !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: execution_backend_id
    if ('execution_backend_id' in data && data.execution_backend_id !== undefined && data.execution_backend_id !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentCreate', errors.join('; '));
    }

    return data as CourseContentCreate;
  }

  safeValidate(data: any): { success: true; data: CourseContentCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentCreate', String(error)) };
    }
  }
}

/**
 * DTO for course content GET responses.
 */
export class CourseContentGetValidator extends BaseValidator<CourseContentGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseContentDeploymentGet": {
      "description": "Get deployment details.",
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
        "course_content_id": {
          "title": "Course Content Id",
          "type": "string"
        },
        "example_version_id": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
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
          "title": "Version Tag"
        },
        "deployment_status": {
          "title": "Deployment Status",
          "type": "string"
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
          "title": "Deployment Message"
        },
        "assigned_at": {
          "format": "date-time",
          "title": "Assigned At",
          "type": "string"
        },
        "deployed_at": {
          "anyOf": [
            {
              "format": "date-time",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Deployed At"
        },
        "last_attempt_at": {
          "anyOf": [
            {
              "format": "date-time",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Last Attempt At"
        },
        "deployment_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Deployment Path"
        },
        "version_identifier": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Version Identifier"
        },
        "deployment_metadata": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "title": "Deployment Metadata"
        },
        "workflow_id": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Workflow Id"
        },
        "example_version": {
          "anyOf": [
            {
              "$ref": "#/$defs/ExampleVersionGet"
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
        "course_content_id",
        "example_version_id",
        "deployment_status",
        "deployment_message",
        "assigned_at",
        "deployed_at",
        "last_attempt_at",
        "deployment_path",
        "version_identifier",
        "deployment_metadata",
        "workflow_id"
      ],
      "title": "CourseContentDeploymentGet",
      "type": "object"
    },
    "CourseContentKindGet": {
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
        "has_ascendants": {
          "title": "Has Ascendants",
          "type": "boolean"
        },
        "has_descendants": {
          "title": "Has Descendants",
          "type": "boolean"
        },
        "submittable": {
          "title": "Submittable",
          "type": "boolean"
        },
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
        }
      },
      "required": [
        "has_ascendants",
        "has_descendants",
        "submittable",
        "id"
      ],
      "title": "CourseContentKindGet",
      "type": "object"
    },
    "CourseContentPropertiesGet": {
      "additionalProperties": true,
      "description": "Properties for course content GET responses.",
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
      "title": "CourseContentPropertiesGet",
      "type": "object"
    },
    "CourseContentTypeGet": {
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
        "slug": {
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
        "color": {
          "title": "Color",
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
        },
        "course_id": {
          "title": "Course Id",
          "type": "string"
        },
        "course_content_kind_id": {
          "title": "Course Content Kind Id",
          "type": "string"
        },
        "course_content_kind": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseContentKindGet"
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
        "slug",
        "color",
        "course_id",
        "course_content_kind_id"
      ],
      "title": "CourseContentTypeGet",
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
    },
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
  "description": "DTO for course content GET responses.",
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
    "archived_at": {
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
      "title": "Archived At"
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
      "title": "Path",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
    },
    "course_content_type_id": {
      "title": "Course Content Type Id",
      "type": "string"
    },
    "course_content_kind_id": {
      "title": "Course Content Kind Id",
      "type": "string"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseContentPropertiesGet"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "position": {
      "title": "Position",
      "type": "number"
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
      "title": "Max Submissions"
    },
    "execution_backend_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Execution Backend Id"
    },
    "is_submittable": {
      "default": false,
      "title": "Is Submittable",
      "type": "boolean"
    },
    "has_deployment": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Has Deployment"
    },
    "deployment_status": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Deployment Status"
    },
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
      "deprecated": true,
      "description": "DEPRECATED: Use deployment API",
      "title": "Example Version Id"
    },
    "course_content_type": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseContentTypeGet"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "deployment": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseContentDeploymentGet"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deployment information if requested via include=deployment"
    }
  },
  "required": [
    "id",
    "path",
    "course_id",
    "course_content_type_id",
    "course_content_kind_id",
    "position"
  ],
  "title": "CourseContentGet",
  "type": "object",
  "x-model-name": "CourseContentGet"
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

  validate(data: any): CourseContentGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentGet', 'Expected an object');
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

    // Optional field: archived_at
    if ('archived_at' in data && data.archived_at !== undefined && data.archived_at !== null) {
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

    // Required field: path
    if (!('path' in data)) {
      errors.push('Missing required field: path');
    } else {
      if (typeof data.path !== 'string') {
        errors.push('Field path must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Required field: course_content_type_id
    if (!('course_content_type_id' in data)) {
      errors.push('Missing required field: course_content_type_id');
    } else {
      if (typeof data.course_content_type_id !== 'string') {
        errors.push('Field course_content_type_id must be a string');
      }
    }

    // Required field: course_content_kind_id
    if (!('course_content_kind_id' in data)) {
      errors.push('Missing required field: course_content_kind_id');
    } else {
      if (typeof data.course_content_kind_id !== 'string') {
        errors.push('Field course_content_kind_id must be a string');
      }
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: position
    if (!('position' in data)) {
      errors.push('Missing required field: position');
    } else {
      if (typeof data.position !== 'number') {
        errors.push('Field position must be a number');
      }
    }

    // Optional field: max_group_size
    if ('max_group_size' in data && data.max_group_size !== undefined && data.max_group_size !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_test_runs
    if ('max_test_runs' in data && data.max_test_runs !== undefined && data.max_test_runs !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_submissions
    if ('max_submissions' in data && data.max_submissions !== undefined && data.max_submissions !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: execution_backend_id
    if ('execution_backend_id' in data && data.execution_backend_id !== undefined && data.execution_backend_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: is_submittable
    if ('is_submittable' in data && data.is_submittable !== undefined && data.is_submittable !== null) {
      if (typeof data.is_submittable !== 'boolean') {
        errors.push('Field is_submittable must be a boolean');
      }
    }

    // Optional field: has_deployment
    if ('has_deployment' in data && data.has_deployment !== undefined && data.has_deployment !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: deployment_status
    if ('deployment_status' in data && data.deployment_status !== undefined && data.deployment_status !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: example_version_id
    if ('example_version_id' in data && data.example_version_id !== undefined && data.example_version_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_content_type
    if ('course_content_type' in data && data.course_content_type !== undefined && data.course_content_type !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: deployment
    if ('deployment' in data && data.deployment !== undefined && data.deployment !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentGet', errors.join('; '));
    }

    return data as CourseContentGet;
  }

  safeValidate(data: any): { success: true; data: CourseContentGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentGet', String(error)) };
    }
  }
}

/**
 * DTO for course content list responses.
 */
export class CourseContentListValidator extends BaseValidator<CourseContentList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseContentDeploymentList": {
      "description": "List view of deployments.",
      "properties": {
        "id": {
          "title": "Id",
          "type": "string"
        },
        "course_content_id": {
          "title": "Course Content Id",
          "type": "string"
        },
        "example_version_id": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
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
          "title": "Version Tag"
        },
        "deployment_status": {
          "title": "Deployment Status",
          "type": "string"
        },
        "assigned_at": {
          "format": "date-time",
          "title": "Assigned At",
          "type": "string"
        },
        "deployed_at": {
          "anyOf": [
            {
              "format": "date-time",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Deployed At"
        },
        "version_identifier": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Version Identifier"
        },
        "example_version": {
          "anyOf": [
            {
              "$ref": "#/$defs/ExampleVersionList"
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
        "course_content_id",
        "example_version_id",
        "deployment_status",
        "assigned_at",
        "deployed_at",
        "version_identifier"
      ],
      "title": "CourseContentDeploymentList",
      "type": "object"
    },
    "CourseContentKindList": {
      "properties": {
        "id": {
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
          "title": "Title"
        },
        "has_ascendants": {
          "title": "Has Ascendants",
          "type": "boolean"
        },
        "has_descendants": {
          "title": "Has Descendants",
          "type": "boolean"
        },
        "submittable": {
          "title": "Submittable",
          "type": "boolean"
        }
      },
      "required": [
        "id",
        "has_ascendants",
        "has_descendants",
        "submittable"
      ],
      "title": "CourseContentKindList",
      "type": "object"
    },
    "CourseContentTypeList": {
      "properties": {
        "id": {
          "title": "Id",
          "type": "string"
        },
        "slug": {
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
          "title": "Title"
        },
        "color": {
          "title": "Color",
          "type": "string"
        },
        "course_id": {
          "title": "Course Id",
          "type": "string"
        },
        "course_content_kind_id": {
          "title": "Course Content Kind Id",
          "type": "string"
        },
        "course_content_kind": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseContentKindList"
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
        "slug",
        "color",
        "course_id",
        "course_content_kind_id"
      ],
      "title": "CourseContentTypeList",
      "type": "object"
    },
    "ExampleVersionList": {
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
      "type": "object"
    }
  },
  "description": "DTO for course content list responses.",
  "properties": {
    "id": {
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
      "title": "Title"
    },
    "path": {
      "title": "Path",
      "type": "string"
    },
    "course_id": {
      "title": "Course Id",
      "type": "string"
    },
    "course_content_type_id": {
      "title": "Course Content Type Id",
      "type": "string"
    },
    "course_content_kind_id": {
      "title": "Course Content Kind Id",
      "type": "string"
    },
    "position": {
      "title": "Position",
      "type": "number"
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
      "title": "Max Submissions"
    },
    "execution_backend_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Execution Backend Id"
    },
    "is_submittable": {
      "default": false,
      "title": "Is Submittable",
      "type": "boolean"
    },
    "course_content_type": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseContentTypeList"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "has_deployment": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Whether this content has an example deployment",
      "title": "Has Deployment"
    },
    "deployment_status": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Current deployment status if has_deployment=true",
      "title": "Deployment Status"
    },
    "deployment": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseContentDeploymentList"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deployment information if requested via include=deployment"
    }
  },
  "required": [
    "id",
    "path",
    "course_id",
    "course_content_type_id",
    "course_content_kind_id",
    "position"
  ],
  "title": "CourseContentList",
  "type": "object",
  "x-model-name": "CourseContentList"
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

  validate(data: any): CourseContentList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentList', 'Expected an object');
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

    // Required field: path
    if (!('path' in data)) {
      errors.push('Missing required field: path');
    } else {
      if (typeof data.path !== 'string') {
        errors.push('Field path must be a string');
      }
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Required field: course_content_type_id
    if (!('course_content_type_id' in data)) {
      errors.push('Missing required field: course_content_type_id');
    } else {
      if (typeof data.course_content_type_id !== 'string') {
        errors.push('Field course_content_type_id must be a string');
      }
    }

    // Required field: course_content_kind_id
    if (!('course_content_kind_id' in data)) {
      errors.push('Missing required field: course_content_kind_id');
    } else {
      if (typeof data.course_content_kind_id !== 'string') {
        errors.push('Field course_content_kind_id must be a string');
      }
    }

    // Required field: position
    if (!('position' in data)) {
      errors.push('Missing required field: position');
    } else {
      if (typeof data.position !== 'number') {
        errors.push('Field position must be a number');
      }
    }

    // Optional field: max_group_size
    if ('max_group_size' in data && data.max_group_size !== undefined && data.max_group_size !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_test_runs
    if ('max_test_runs' in data && data.max_test_runs !== undefined && data.max_test_runs !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_submissions
    if ('max_submissions' in data && data.max_submissions !== undefined && data.max_submissions !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: execution_backend_id
    if ('execution_backend_id' in data && data.execution_backend_id !== undefined && data.execution_backend_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: is_submittable
    if ('is_submittable' in data && data.is_submittable !== undefined && data.is_submittable !== null) {
      if (typeof data.is_submittable !== 'boolean') {
        errors.push('Field is_submittable must be a boolean');
      }
    }

    // Optional field: course_content_type
    if ('course_content_type' in data && data.course_content_type !== undefined && data.course_content_type !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: has_deployment
    if ('has_deployment' in data && data.has_deployment !== undefined && data.has_deployment !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: deployment_status
    if ('deployment_status' in data && data.deployment_status !== undefined && data.deployment_status !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: deployment
    if ('deployment' in data && data.deployment !== undefined && data.deployment !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentList', errors.join('; '));
    }

    return data as CourseContentList;
  }

  safeValidate(data: any): { success: true; data: CourseContentList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentList', String(error)) };
    }
  }
}

/**
 * DTO for updating course content.
 */
export class CourseContentUpdateValidator extends BaseValidator<CourseContentUpdate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseContentProperties": {
      "additionalProperties": true,
      "description": "Properties for course content (stored in JSONB).",
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
      "title": "CourseContentProperties",
      "type": "object"
    },
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
  "description": "DTO for updating course content.",
  "properties": {
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
    "course_content_type_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Content Type Id"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseContentProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null
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
      "title": "Max Submissions"
    },
    "execution_backend_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Execution Backend Id"
    }
  },
  "title": "CourseContentUpdate",
  "type": "object",
  "x-model-name": "CourseContentUpdate"
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

  validate(data: any): CourseContentUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentUpdate', 'Expected an object');
    }

    // Optional field: path
    if ('path' in data && data.path !== undefined && data.path !== null) {
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

    // Optional field: course_content_type_id
    if ('course_content_type_id' in data && data.course_content_type_id !== undefined && data.course_content_type_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: position
    if ('position' in data && data.position !== undefined && data.position !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_group_size
    if ('max_group_size' in data && data.max_group_size !== undefined && data.max_group_size !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_test_runs
    if ('max_test_runs' in data && data.max_test_runs !== undefined && data.max_test_runs !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_submissions
    if ('max_submissions' in data && data.max_submissions !== undefined && data.max_submissions !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: execution_backend_id
    if ('execution_backend_id' in data && data.execution_backend_id !== undefined && data.execution_backend_id !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentUpdate', errors.join('; '));
    }

    return data as CourseContentUpdate;
  }

  safeValidate(data: any): { success: true; data: CourseContentUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentUpdate', String(error)) };
    }
  }
}

/**
 * Query parameters for course content.
 */
export class CourseContentQueryValidator extends BaseValidator<CourseContentQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseContentProperties": {
      "additionalProperties": true,
      "description": "Properties for course content (stored in JSONB).",
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
      "title": "CourseContentProperties",
      "type": "object"
    },
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
  "description": "Query parameters for course content.",
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
    },
    "course_content_type_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Content Type Id"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CourseContentProperties"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "archived": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Archived"
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
      "title": "Max Submissions"
    },
    "execution_backend_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Execution Backend Id"
    },
    "has_deployment": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Filter by whether content has a deployment",
      "title": "Has Deployment"
    }
  },
  "title": "CourseContentQuery",
  "type": "object",
  "x-model-name": "CourseContentQuery"
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

  validate(data: any): CourseContentQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentQuery', 'Expected an object');
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

    // Optional field: path
    if ('path' in data && data.path !== undefined && data.path !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_id
    if ('course_id' in data && data.course_id !== undefined && data.course_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_content_type_id
    if ('course_content_type_id' in data && data.course_content_type_id !== undefined && data.course_content_type_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: archived
    if ('archived' in data && data.archived !== undefined && data.archived !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: position
    if ('position' in data && data.position !== undefined && data.position !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_group_size
    if ('max_group_size' in data && data.max_group_size !== undefined && data.max_group_size !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_test_runs
    if ('max_test_runs' in data && data.max_test_runs !== undefined && data.max_test_runs !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: max_submissions
    if ('max_submissions' in data && data.max_submissions !== undefined && data.max_submissions !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: execution_backend_id
    if ('execution_backend_id' in data && data.execution_backend_id !== undefined && data.execution_backend_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: has_deployment
    if ('has_deployment' in data && data.has_deployment !== undefined && data.has_deployment !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentQuery', errors.join('; '));
    }

    return data as CourseContentQuery;
  }

  safeValidate(data: any): { success: true; data: CourseContentQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentQuery', String(error)) };
    }
  }
}

/**
 * Validator for CourseMemberCommentCreate
 */
export class CourseMemberCommentCreateValidator extends BaseValidator<CourseMemberCommentCreate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
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
    "transmitter_id": {
      "default": null,
      "title": "Transmitter Id",
      "type": "string"
    },
    "course_member_id": {
      "title": "Course Member Id",
      "type": "string"
    },
    "message": {
      "title": "Message",
      "type": "string"
    }
  },
  "required": [
    "course_member_id",
    "message"
  ],
  "title": "CourseMemberCommentCreate",
  "type": "object",
  "x-model-name": "CourseMemberCommentCreate"
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

  validate(data: any): CourseMemberCommentCreate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseMemberCommentCreate', 'Expected an object');
    }

    // Optional field: id
    if ('id' in data && data.id !== undefined && data.id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: transmitter_id
    if ('transmitter_id' in data && data.transmitter_id !== undefined && data.transmitter_id !== null) {
      if (typeof data.transmitter_id !== 'string') {
        errors.push('Field transmitter_id must be a string');
      }
    }

    // Required field: course_member_id
    if (!('course_member_id' in data)) {
      errors.push('Missing required field: course_member_id');
    } else {
      if (typeof data.course_member_id !== 'string') {
        errors.push('Field course_member_id must be a string');
      }
    }

    // Required field: message
    if (!('message' in data)) {
      errors.push('Missing required field: message');
    } else {
      if (typeof data.message !== 'string') {
        errors.push('Field message must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseMemberCommentCreate', errors.join('; '));
    }

    return data as CourseMemberCommentCreate;
  }

  safeValidate(data: any): { success: true; data: CourseMemberCommentCreate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseMemberCommentCreate', String(error)) };
    }
  }
}

/**
 * Validator for CourseMemberCommentGet
 */
export class CourseMemberCommentGetValidator extends BaseValidator<CourseMemberCommentGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseMemberGet": {
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
        "properties": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseMemberProperties"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "user_id": {
          "title": "User Id",
          "type": "string"
        },
        "course_id": {
          "title": "Course Id",
          "type": "string"
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
        "course_role_id": {
          "title": "Course Role Id",
          "type": "string"
        },
        "user": {
          "anyOf": [
            {
              "$ref": "#/$defs/UserList"
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
        "user_id",
        "course_id",
        "course_role_id"
      ],
      "title": "CourseMemberGet",
      "type": "object"
    },
    "CourseMemberGitLabConfig": {
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
        "full_path_submission": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path Submission"
        }
      },
      "title": "CourseMemberGitLabConfig",
      "type": "object"
    },
    "CourseMemberProperties": {
      "additionalProperties": true,
      "properties": {
        "gitlab": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseMemberGitLabConfig"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "CourseMemberProperties",
      "type": "object"
    },
    "UserList": {
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
          "description": "User unique identifier",
          "title": "Id",
          "type": "string"
        },
        "given_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "User's given name",
          "title": "Given Name"
        },
        "family_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "User's family name",
          "title": "Family Name"
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
          "description": "User's email address",
          "title": "Email"
        },
        "user_type": {
          "anyOf": [
            {
              "$ref": "#/$defs/UserTypeEnum"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Type of user account"
        },
        "username": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Unique username",
          "title": "Username"
        },
        "archived_at": {
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
          "description": "Archive timestamp",
          "title": "Archived At"
        }
      },
      "required": [
        "id"
      ],
      "title": "UserList",
      "type": "object"
    },
    "UserTypeEnum": {
      "enum": [
        "user",
        "token"
      ],
      "title": "UserTypeEnum",
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
      "title": "Id",
      "type": "string"
    },
    "transmitter_id": {
      "default": null,
      "title": "Transmitter Id",
      "type": "string"
    },
    "transmitter": {
      "$ref": "#/$defs/CourseMemberGet"
    },
    "course_member_id": {
      "title": "Course Member Id",
      "type": "string"
    },
    "message": {
      "title": "Message",
      "type": "string"
    }
  },
  "required": [
    "id",
    "transmitter",
    "course_member_id",
    "message"
  ],
  "title": "CourseMemberCommentGet",
  "type": "object",
  "x-model-name": "CourseMemberCommentGet"
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

  validate(data: any): CourseMemberCommentGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseMemberCommentGet', 'Expected an object');
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

    // Optional field: transmitter_id
    if ('transmitter_id' in data && data.transmitter_id !== undefined && data.transmitter_id !== null) {
      if (typeof data.transmitter_id !== 'string') {
        errors.push('Field transmitter_id must be a string');
      }
    }

    // Required field: transmitter
    if (!('transmitter' in data)) {
      errors.push('Missing required field: transmitter');
    } else {
      // Reference field - basic object check
      if (typeof data.transmitter !== 'object') {
        errors.push('Field transmitter must be an object');
      }
    }

    // Required field: course_member_id
    if (!('course_member_id' in data)) {
      errors.push('Missing required field: course_member_id');
    } else {
      if (typeof data.course_member_id !== 'string') {
        errors.push('Field course_member_id must be a string');
      }
    }

    // Required field: message
    if (!('message' in data)) {
      errors.push('Missing required field: message');
    } else {
      if (typeof data.message !== 'string') {
        errors.push('Field message must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseMemberCommentGet', errors.join('; '));
    }

    return data as CourseMemberCommentGet;
  }

  safeValidate(data: any): { success: true; data: CourseMemberCommentGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseMemberCommentGet', String(error)) };
    }
  }
}

/**
 * Validator for CourseMemberCommentList
 */
export class CourseMemberCommentListValidator extends BaseValidator<CourseMemberCommentList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseMemberList": {
      "properties": {
        "id": {
          "title": "Id",
          "type": "string"
        },
        "user_id": {
          "title": "User Id",
          "type": "string"
        },
        "course_id": {
          "title": "Course Id",
          "type": "string"
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
        "course_role_id": {
          "title": "Course Role Id",
          "type": "string"
        },
        "user": {
          "$ref": "#/$defs/UserList"
        }
      },
      "required": [
        "id",
        "user_id",
        "course_id",
        "course_role_id",
        "user"
      ],
      "title": "CourseMemberList",
      "type": "object"
    },
    "UserList": {
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
          "description": "User unique identifier",
          "title": "Id",
          "type": "string"
        },
        "given_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "User's given name",
          "title": "Given Name"
        },
        "family_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "User's family name",
          "title": "Family Name"
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
          "description": "User's email address",
          "title": "Email"
        },
        "user_type": {
          "anyOf": [
            {
              "$ref": "#/$defs/UserTypeEnum"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Type of user account"
        },
        "username": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Unique username",
          "title": "Username"
        },
        "archived_at": {
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
          "description": "Archive timestamp",
          "title": "Archived At"
        }
      },
      "required": [
        "id"
      ],
      "title": "UserList",
      "type": "object"
    },
    "UserTypeEnum": {
      "enum": [
        "user",
        "token"
      ],
      "title": "UserTypeEnum",
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
      "title": "Id",
      "type": "string"
    },
    "transmitter_id": {
      "default": null,
      "title": "Transmitter Id",
      "type": "string"
    },
    "transmitter": {
      "$ref": "#/$defs/CourseMemberList"
    },
    "course_member_id": {
      "title": "Course Member Id",
      "type": "string"
    },
    "message": {
      "title": "Message",
      "type": "string"
    }
  },
  "required": [
    "id",
    "transmitter",
    "course_member_id",
    "message"
  ],
  "title": "CourseMemberCommentList",
  "type": "object",
  "x-model-name": "CourseMemberCommentList"
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

  validate(data: any): CourseMemberCommentList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseMemberCommentList', 'Expected an object');
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

    // Optional field: transmitter_id
    if ('transmitter_id' in data && data.transmitter_id !== undefined && data.transmitter_id !== null) {
      if (typeof data.transmitter_id !== 'string') {
        errors.push('Field transmitter_id must be a string');
      }
    }

    // Required field: transmitter
    if (!('transmitter' in data)) {
      errors.push('Missing required field: transmitter');
    } else {
      // Reference field - basic object check
      if (typeof data.transmitter !== 'object') {
        errors.push('Field transmitter must be an object');
      }
    }

    // Required field: course_member_id
    if (!('course_member_id' in data)) {
      errors.push('Missing required field: course_member_id');
    } else {
      if (typeof data.course_member_id !== 'string') {
        errors.push('Field course_member_id must be a string');
      }
    }

    // Required field: message
    if (!('message' in data)) {
      errors.push('Missing required field: message');
    } else {
      if (typeof data.message !== 'string') {
        errors.push('Field message must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseMemberCommentList', errors.join('; '));
    }

    return data as CourseMemberCommentList;
  }

  safeValidate(data: any): { success: true; data: CourseMemberCommentList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseMemberCommentList', String(error)) };
    }
  }
}

/**
 * Validator for CourseMemberCommentUpdate
 */
export class CourseMemberCommentUpdateValidator extends BaseValidator<CourseMemberCommentUpdate> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "message": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Message"
    }
  },
  "title": "CourseMemberCommentUpdate",
  "type": "object",
  "x-model-name": "CourseMemberCommentUpdate"
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

  validate(data: any): CourseMemberCommentUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseMemberCommentUpdate', 'Expected an object');
    }

    // Optional field: message
    if ('message' in data && data.message !== undefined && data.message !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseMemberCommentUpdate', errors.join('; '));
    }

    return data as CourseMemberCommentUpdate;
  }

  safeValidate(data: any): { success: true; data: CourseMemberCommentUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseMemberCommentUpdate', String(error)) };
    }
  }
}

/**
 * Validator for CourseMemberCommentQuery
 */
export class CourseMemberCommentQueryValidator extends BaseValidator<CourseMemberCommentQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    "transmitter_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Transmitter Id"
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
    }
  },
  "title": "CourseMemberCommentQuery",
  "type": "object",
  "x-model-name": "CourseMemberCommentQuery"
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

  validate(data: any): CourseMemberCommentQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseMemberCommentQuery', 'Expected an object');
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

    // Optional field: transmitter_id
    if ('transmitter_id' in data && data.transmitter_id !== undefined && data.transmitter_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: course_member_id
    if ('course_member_id' in data && data.course_member_id !== undefined && data.course_member_id !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseMemberCommentQuery', errors.join('; '));
    }

    return data as CourseMemberCommentQuery;
  }

  safeValidate(data: any): { success: true; data: CourseMemberCommentQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseMemberCommentQuery', String(error)) };
    }
  }
}

/**
 * Validator for CourseTutorRepository
 */
export class CourseTutorRepositoryValidator extends BaseValidator<CourseTutorRepository> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "provider_url": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Provider Url"
    },
    "full_path_reference": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Full Path Reference"
    }
  },
  "title": "CourseTutorRepository",
  "type": "object",
  "x-model-name": "CourseTutorRepository"
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

  validate(data: any): CourseTutorRepository {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseTutorRepository', 'Expected an object');
    }

    // Optional field: provider_url
    if ('provider_url' in data && data.provider_url !== undefined && data.provider_url !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: full_path_reference
    if ('full_path_reference' in data && data.full_path_reference !== undefined && data.full_path_reference !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseTutorRepository', errors.join('; '));
    }

    return data as CourseTutorRepository;
  }

  safeValidate(data: any): { success: true; data: CourseTutorRepository } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseTutorRepository', String(error)) };
    }
  }
}

/**
 * Validator for CourseTutorGet
 */
export class CourseTutorGetValidator extends BaseValidator<CourseTutorGet> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseTutorRepository": {
      "properties": {
        "provider_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Provider Url"
        },
        "full_path_reference": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path Reference"
        }
      },
      "title": "CourseTutorRepository",
      "type": "object"
    }
  },
  "properties": {
    "id": {
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
      "title": "Title"
    },
    "course_family_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Family Id"
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
    "path": {
      "title": "Path",
      "type": "string"
    },
    "repository": {
      "$ref": "#/$defs/CourseTutorRepository"
    }
  },
  "required": [
    "id",
    "path",
    "repository"
  ],
  "title": "CourseTutorGet",
  "type": "object",
  "x-model-name": "CourseTutorGet"
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

  validate(data: any): CourseTutorGet {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseTutorGet', 'Expected an object');
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

    // Optional field: course_family_id
    if ('course_family_id' in data && data.course_family_id !== undefined && data.course_family_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: organization_id
    if ('organization_id' in data && data.organization_id !== undefined && data.organization_id !== null) {
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

    // Required field: repository
    if (!('repository' in data)) {
      errors.push('Missing required field: repository');
    } else {
      // Reference field - basic object check
      if (typeof data.repository !== 'object') {
        errors.push('Field repository must be an object');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseTutorGet', errors.join('; '));
    }

    return data as CourseTutorGet;
  }

  safeValidate(data: any): { success: true; data: CourseTutorGet } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseTutorGet', String(error)) };
    }
  }
}

/**
 * Validator for CourseTutorList
 */
export class CourseTutorListValidator extends BaseValidator<CourseTutorList> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CourseTutorRepository": {
      "properties": {
        "provider_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Provider Url"
        },
        "full_path_reference": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Full Path Reference"
        }
      },
      "title": "CourseTutorRepository",
      "type": "object"
    }
  },
  "properties": {
    "id": {
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
      "title": "Title"
    },
    "course_family_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Family Id"
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
    "path": {
      "title": "Path",
      "type": "string"
    },
    "repository": {
      "$ref": "#/$defs/CourseTutorRepository"
    }
  },
  "required": [
    "id",
    "path",
    "repository"
  ],
  "title": "CourseTutorList",
  "type": "object",
  "x-model-name": "CourseTutorList"
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

  validate(data: any): CourseTutorList {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseTutorList', 'Expected an object');
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

    // Optional field: course_family_id
    if ('course_family_id' in data && data.course_family_id !== undefined && data.course_family_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: organization_id
    if ('organization_id' in data && data.organization_id !== undefined && data.organization_id !== null) {
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

    // Required field: repository
    if (!('repository' in data)) {
      errors.push('Missing required field: repository');
    } else {
      // Reference field - basic object check
      if (typeof data.repository !== 'object') {
        errors.push('Field repository must be an object');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseTutorList', errors.join('; '));
    }

    return data as CourseTutorList;
  }

  safeValidate(data: any): { success: true; data: CourseTutorList } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseTutorList', String(error)) };
    }
  }
}

/**
 * Validator for CourseTutorQuery
 */
export class CourseTutorQueryValidator extends BaseValidator<CourseTutorQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
    "course_family_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Course Family Id"
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
  "title": "CourseTutorQuery",
  "type": "object",
  "x-model-name": "CourseTutorQuery"
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

  validate(data: any): CourseTutorQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseTutorQuery', 'Expected an object');
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

    // Optional field: course_family_id
    if ('course_family_id' in data && data.course_family_id !== undefined && data.course_family_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: organization_id
    if ('organization_id' in data && data.organization_id !== undefined && data.organization_id !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseTutorQuery', errors.join('; '));
    }

    return data as CourseTutorQuery;
  }

  safeValidate(data: any): { success: true; data: CourseTutorQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseTutorQuery', String(error)) };
    }
  }
}

/**
 * Course content type configuration for deployment.
 */
export class CourseContentTypeConfigValidator extends BaseValidator<CourseContentTypeConfig> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
  "type": "object",
  "x-model-name": "CourseContentTypeConfig"
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

  validate(data: any): CourseContentTypeConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentTypeConfig', 'Expected an object');
    }

    // Required field: slug
    if (!('slug' in data)) {
      errors.push('Missing required field: slug');
    } else {
      if (typeof data.slug !== 'string') {
        errors.push('Field slug must be a string');
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

    // Optional field: color
    if ('color' in data && data.color !== undefined && data.color !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: kind
    if (!('kind' in data)) {
      errors.push('Missing required field: kind');
    } else {
      if (typeof data.kind !== 'string') {
        errors.push('Field kind must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentTypeConfig', errors.join('; '));
    }

    return data as CourseContentTypeConfig;
  }

  safeValidate(data: any): { success: true; data: CourseContentTypeConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentTypeConfig', String(error)) };
    }
  }
}

/**
 * Configuration for course-related GitLab projects.
 */
export class CourseProjectsValidator extends BaseValidator<CourseProjects> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
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
  "type": "object",
  "x-model-name": "CourseProjects"
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

  validate(data: any): CourseProjects {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseProjects', 'Expected an object');
    }

    // Optional field: tests
    if ('tests' in data && data.tests !== undefined && data.tests !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: student_template
    if ('student_template' in data && data.student_template !== undefined && data.student_template !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: reference
    if ('reference' in data && data.reference !== undefined && data.reference !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: examples
    if ('examples' in data && data.examples !== undefined && data.examples !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: documents
    if ('documents' in data && data.documents !== undefined && data.documents !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseProjects', errors.join('; '));
    }

    return data as CourseProjects;
  }

  safeValidate(data: any): { success: true; data: CourseProjects } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseProjects', String(error)) };
    }
  }
}

/**
 * Course family configuration.
 */
export class CourseFamilyConfigValidator extends BaseValidator<CourseFamilyConfig> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Course family configuration.",
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
    }
  },
  "required": [
    "name",
    "path"
  ],
  "title": "CourseFamilyConfig",
  "type": "object",
  "x-model-name": "CourseFamilyConfig"
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

  validate(data: any): CourseFamilyConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseFamilyConfig', 'Expected an object');
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

    if (errors.length > 0) {
      throw new ValidationError('CourseFamilyConfig', errors.join('; '));
    }

    return data as CourseFamilyConfig;
  }

  safeValidate(data: any): { success: true; data: CourseFamilyConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseFamilyConfig', String(error)) };
    }
  }
}

/**
 * Configuration for course content (assignments, units, etc.).
 */
export class CourseContentConfigValidator extends BaseValidator<CourseContentConfig> {
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
    }
  },
  "$ref": "#/$defs/CourseContentConfig",
  "x-model-name": "CourseContentConfig",
  "description": "Configuration for course content (assignments, units, etc.)."
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

  validate(data: any): CourseContentConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentConfig', 'Expected an object');
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentConfig', errors.join('; '));
    }

    return data as CourseContentConfig;
  }

  safeValidate(data: any): { success: true; data: CourseContentConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentConfig', String(error)) };
    }
  }
}

/**
 * Course configuration.
 */
export class CourseConfigValidator extends BaseValidator<CourseConfig> {
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
    }
  },
  "description": "Course configuration.",
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
  "title": "CourseConfig",
  "type": "object",
  "x-model-name": "CourseConfig"
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

  validate(data: any): CourseConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseConfig', 'Expected an object');
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

    // Optional field: projects
    if ('projects' in data && data.projects !== undefined && data.projects !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: execution_backends
    if ('execution_backends' in data && data.execution_backends !== undefined && data.execution_backends !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: content_types
    if ('content_types' in data && data.content_types !== undefined && data.content_types !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: contents
    if ('contents' in data && data.contents !== undefined && data.contents !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: settings
    if ('settings' in data && data.settings !== undefined && data.settings !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseConfig', errors.join('; '));
    }

    return data as CourseConfig;
  }

  safeValidate(data: any): { success: true; data: CourseConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseConfig', String(error)) };
    }
  }
}

/**
 * Course configuration for hierarchical deployment.
 */
export class HierarchicalCourseConfigValidator extends BaseValidator<HierarchicalCourseConfig> {
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
    }
  },
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
  "type": "object",
  "x-model-name": "HierarchicalCourseConfig"
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

  validate(data: any): HierarchicalCourseConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('HierarchicalCourseConfig', 'Expected an object');
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

    // Optional field: projects
    if ('projects' in data && data.projects !== undefined && data.projects !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: execution_backends
    if ('execution_backends' in data && data.execution_backends !== undefined && data.execution_backends !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: content_types
    if ('content_types' in data && data.content_types !== undefined && data.content_types !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: contents
    if ('contents' in data && data.contents !== undefined && data.contents !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: settings
    if ('settings' in data && data.settings !== undefined && data.settings !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('HierarchicalCourseConfig', errors.join('; '));
    }

    return data as HierarchicalCourseConfig;
  }

  safeValidate(data: any): { success: true; data: HierarchicalCourseConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('HierarchicalCourseConfig', String(error)) };
    }
  }
}

/**
 * Course family configuration with nested courses.
 */
export class HierarchicalCourseFamilyConfigValidator extends BaseValidator<HierarchicalCourseFamilyConfig> {
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
    }
  },
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
  "type": "object",
  "x-model-name": "HierarchicalCourseFamilyConfig"
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

  validate(data: any): HierarchicalCourseFamilyConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('HierarchicalCourseFamilyConfig', 'Expected an object');
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

    // Optional field: courses
    if ('courses' in data && data.courses !== undefined && data.courses !== null) {
      if (!Array.isArray(data.courses)) {
        errors.push('Field courses must be an array');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('HierarchicalCourseFamilyConfig', errors.join('; '));
    }

    return data as HierarchicalCourseFamilyConfig;
  }

  safeValidate(data: any): { success: true; data: HierarchicalCourseFamilyConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('HierarchicalCourseFamilyConfig', String(error)) };
    }
  }
}

/**
 * Validator for CourseProjectsConfig
 */
export class CourseProjectsConfigValidator extends BaseValidator<CourseProjectsConfig> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "GitlabGroupProjectConfig": {
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
        "path": {
          "title": "Path",
          "type": "string"
        }
      },
      "required": [
        "path"
      ],
      "title": "GitlabGroupProjectConfig",
      "type": "object"
    }
  },
  "properties": {
    "tests": {
      "$ref": "#/$defs/GitlabGroupProjectConfig"
    },
    "student_template": {
      "$ref": "#/$defs/GitlabGroupProjectConfig"
    },
    "reference": {
      "$ref": "#/$defs/GitlabGroupProjectConfig"
    },
    "images": {
      "$ref": "#/$defs/GitlabGroupProjectConfig"
    },
    "documents": {
      "$ref": "#/$defs/GitlabGroupProjectConfig"
    }
  },
  "required": [
    "tests",
    "student_template",
    "reference",
    "images",
    "documents"
  ],
  "title": "CourseProjectsConfig",
  "type": "object",
  "x-model-name": "CourseProjectsConfig"
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

  validate(data: any): CourseProjectsConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseProjectsConfig', 'Expected an object');
    }

    // Required field: tests
    if (!('tests' in data)) {
      errors.push('Missing required field: tests');
    } else {
      // Reference field - basic object check
      if (typeof data.tests !== 'object') {
        errors.push('Field tests must be an object');
      }
    }

    // Required field: student_template
    if (!('student_template' in data)) {
      errors.push('Missing required field: student_template');
    } else {
      // Reference field - basic object check
      if (typeof data.student_template !== 'object') {
        errors.push('Field student_template must be an object');
      }
    }

    // Required field: reference
    if (!('reference' in data)) {
      errors.push('Missing required field: reference');
    } else {
      // Reference field - basic object check
      if (typeof data.reference !== 'object') {
        errors.push('Field reference must be an object');
      }
    }

    // Required field: images
    if (!('images' in data)) {
      errors.push('Missing required field: images');
    } else {
      // Reference field - basic object check
      if (typeof data.images !== 'object') {
        errors.push('Field images must be an object');
      }
    }

    // Required field: documents
    if (!('documents' in data)) {
      errors.push('Missing required field: documents');
    } else {
      // Reference field - basic object check
      if (typeof data.documents !== 'object') {
        errors.push('Field documents must be an object');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseProjectsConfig', errors.join('; '));
    }

    return data as CourseProjectsConfig;
  }

  safeValidate(data: any): { success: true; data: CourseProjectsConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseProjectsConfig', String(error)) };
    }
  }
}

/**
 * Validator for CourseGroupConfig
 */
export class CourseGroupConfigValidator extends BaseValidator<CourseGroupConfig> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "name": {
      "title": "Name",
      "type": "string"
    }
  },
  "required": [
    "name"
  ],
  "title": "CourseGroupConfig",
  "type": "object",
  "x-model-name": "CourseGroupConfig"
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

  validate(data: any): CourseGroupConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseGroupConfig', 'Expected an object');
    }

    // Required field: name
    if (!('name' in data)) {
      errors.push('Missing required field: name');
    } else {
      if (typeof data.name !== 'string') {
        errors.push('Field name must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseGroupConfig', errors.join('; '));
    }

    return data as CourseGroupConfig;
  }

  safeValidate(data: any): { success: true; data: CourseGroupConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseGroupConfig', String(error)) };
    }
  }
}

/**
 * Validator for CourseSettingsConfig
 */
export class CourseSettingsConfigValidator extends BaseValidator<CourseSettingsConfig> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "FileSourceConfig": {
      "properties": {
        "url": {
          "title": "Url",
          "type": "string"
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
      "required": [
        "url"
      ],
      "title": "FileSourceConfig",
      "type": "object"
    }
  },
  "additionalProperties": true,
  "properties": {
    "source": {
      "anyOf": [
        {
          "$ref": "#/$defs/FileSourceConfig"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "title": "CourseSettingsConfig",
  "type": "object",
  "x-model-name": "CourseSettingsConfig"
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

  validate(data: any): CourseSettingsConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseSettingsConfig', 'Expected an object');
    }

    // Optional field: source
    if ('source' in data && data.source !== undefined && data.source !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseSettingsConfig', errors.join('; '));
    }

    return data as CourseSettingsConfig;
  }

  safeValidate(data: any): { success: true; data: CourseSettingsConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseSettingsConfig', String(error)) };
    }
  }
}

/**
 * Validator for CodeAbilityCourseMeta
 */
export class CodeAbilityCourseMetaValidator extends BaseValidator<CodeAbilityCourseMeta> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "CodeAbilityLink": {
      "properties": {
        "description": {
          "minLength": 0,
          "title": "Description",
          "type": "string"
        },
        "url": {
          "minLength": 1,
          "title": "Url",
          "type": "string"
        }
      },
      "required": [
        "description",
        "url"
      ],
      "title": "CodeAbilityLink",
      "type": "object"
    },
    "CodeAbilityMetaProperty": {
      "properties": {
        "studentSubmissionFiles": {
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
          "default": [],
          "title": "Studentsubmissionfiles"
        },
        "additionalFiles": {
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
          "default": [],
          "title": "Additionalfiles"
        },
        "testFiles": {
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
          "default": [],
          "title": "Testfiles"
        },
        "studentTemplates": {
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
          "default": [],
          "title": "Studenttemplates"
        },
        "executionBackend": {
          "anyOf": [
            {
              "$ref": "#/$defs/CourseExecutionBackendConfig"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "maxTestRuns": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Maxtestruns"
        },
        "maxSubmissions": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Maxsubmissions"
        },
        "maxGroupSize": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Maxgroupsize"
        }
      },
      "title": "CodeAbilityMetaProperty",
      "type": "object"
    },
    "CodeAbilityPerson": {
      "properties": {
        "name": {
          "anyOf": [
            {
              "minLength": 1,
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Name"
        },
        "email": {
          "anyOf": [
            {
              "minLength": 1,
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Email"
        },
        "affiliation": {
          "anyOf": [
            {
              "minLength": 1,
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Affiliation"
        }
      },
      "title": "CodeAbilityPerson",
      "type": "object"
    },
    "CourseExecutionBackendConfig": {
      "properties": {
        "slug": {
          "title": "Slug",
          "type": "string"
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
          "default": null,
          "title": "Settings"
        }
      },
      "required": [
        "slug"
      ],
      "title": "CourseExecutionBackendConfig",
      "type": "object"
    },
    "LanguageEnum": {
      "enum": [
        "de",
        "en"
      ],
      "title": "LanguageEnum",
      "type": "string"
    },
    "MetaTypeEnum": {
      "enum": [
        "course",
        "unit",
        "assignment"
      ],
      "title": "MetaTypeEnum",
      "type": "string"
    },
    "TypeConfig": {
      "properties": {
        "kind": {
          "title": "Kind",
          "type": "string"
        },
        "slug": {
          "title": "Slug",
          "type": "string"
        },
        "title": {
          "title": "Title",
          "type": "string"
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
          "default": null,
          "title": "Color"
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
        "properties": {
          "type": "object",
          "additionalProperties": true,
          "default": {},
          "title": "Properties"
        }
      },
      "required": [
        "kind",
        "slug",
        "title"
      ],
      "title": "TypeConfig",
      "type": "object"
    }
  },
  "properties": {
    "version": {
      "anyOf": [
        {
          "pattern": "^([1-9]\\\\d*|0)(\\\\.(([1-9]\\\\d*)|0)){0,3}$",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": "1.0",
      "title": "Version"
    },
    "kind": {
      "anyOf": [
        {
          "$ref": "#/$defs/MetaTypeEnum"
        },
        {
          "type": "null"
        }
      ],
      "default": "assignment"
    },
    "title": {
      "anyOf": [
        {
          "minLength": 1,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": "TITLE",
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
    "language": {
      "anyOf": [
        {
          "$ref": "#/$defs/LanguageEnum"
        },
        {
          "type": "null"
        }
      ],
      "default": "en"
    },
    "license": {
      "anyOf": [
        {
          "minLength": 1,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": "Not specified",
      "title": "License"
    },
    "authors": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/CodeAbilityPerson"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": [],
      "title": "Authors"
    },
    "maintainers": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/CodeAbilityPerson"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": [],
      "title": "Maintainers"
    },
    "links": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/CodeAbilityLink"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": [],
      "title": "Links"
    },
    "supportingMaterial": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/CodeAbilityLink"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": [],
      "title": "Supportingmaterial"
    },
    "keywords": {
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
      "default": [],
      "title": "Keywords"
    },
    "properties": {
      "anyOf": [
        {
          "$ref": "#/$defs/CodeAbilityMetaProperty"
        },
        {
          "type": "null"
        }
      ],
      "default": {
        "studentSubmissionFiles": [],
        "additionalFiles": [],
        "testFiles": [],
        "studentTemplates": [],
        "executionBackend": null,
        "maxTestRuns": null,
        "maxSubmissions": null,
        "maxGroupSize": null
      }
    },
    "contentTypes": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/TypeConfig"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": [],
      "title": "Contenttypes"
    },
    "executionBackends": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/CourseExecutionBackendConfig"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": [],
      "title": "Executionbackends"
    }
  },
  "title": "CodeAbilityCourseMeta",
  "type": "object",
  "x-model-name": "CodeAbilityCourseMeta"
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

  validate(data: any): CodeAbilityCourseMeta {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CodeAbilityCourseMeta', 'Expected an object');
    }

    // Optional field: version
    if ('version' in data && data.version !== undefined && data.version !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: kind
    if ('kind' in data && data.kind !== undefined && data.kind !== null) {
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

    // Optional field: language
    if ('language' in data && data.language !== undefined && data.language !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: license
    if ('license' in data && data.license !== undefined && data.license !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: authors
    if ('authors' in data && data.authors !== undefined && data.authors !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: maintainers
    if ('maintainers' in data && data.maintainers !== undefined && data.maintainers !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: links
    if ('links' in data && data.links !== undefined && data.links !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: supportingMaterial
    if ('supportingMaterial' in data && data.supportingMaterial !== undefined && data.supportingMaterial !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: keywords
    if ('keywords' in data && data.keywords !== undefined && data.keywords !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: properties
    if ('properties' in data && data.properties !== undefined && data.properties !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: contentTypes
    if ('contentTypes' in data && data.contentTypes !== undefined && data.contentTypes !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: executionBackends
    if ('executionBackends' in data && data.executionBackends !== undefined && data.executionBackends !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CodeAbilityCourseMeta', errors.join('; '));
    }

    return data as CodeAbilityCourseMeta;
  }

  safeValidate(data: any): { success: true; data: CodeAbilityCourseMeta } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CodeAbilityCourseMeta', String(error)) };
    }
  }
}

/**
 * Validator for CourseSignupResponse
 */
export class CourseSignupResponseValidator extends BaseValidator<CourseSignupResponse> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "course_id": {
      "title": "Course Id",
      "type": "string"
    },
    "course_title": {
      "title": "Course Title",
      "type": "string"
    },
    "role": {
      "title": "Role",
      "type": "string"
    },
    "repository": {
      "title": "Repository",
      "type": "string"
    }
  },
  "required": [
    "course_id",
    "course_title",
    "role",
    "repository"
  ],
  "title": "CourseSignupResponse",
  "type": "object",
  "x-model-name": "CourseSignupResponse"
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

  validate(data: any): CourseSignupResponse {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseSignupResponse', 'Expected an object');
    }

    // Required field: course_id
    if (!('course_id' in data)) {
      errors.push('Missing required field: course_id');
    } else {
      if (typeof data.course_id !== 'string') {
        errors.push('Field course_id must be a string');
      }
    }

    // Required field: course_title
    if (!('course_title' in data)) {
      errors.push('Missing required field: course_title');
    } else {
      if (typeof data.course_title !== 'string') {
        errors.push('Field course_title must be a string');
      }
    }

    // Required field: role
    if (!('role' in data)) {
      errors.push('Missing required field: role');
    } else {
      if (typeof data.role !== 'string') {
        errors.push('Field role must be a string');
      }
    }

    // Required field: repository
    if (!('repository' in data)) {
      errors.push('Missing required field: repository');
    } else {
      if (typeof data.repository !== 'string') {
        errors.push('Field repository must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseSignupResponse', errors.join('; '));
    }

    return data as CourseSignupResponse;
  }

  safeValidate(data: any): { success: true; data: CourseSignupResponse } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseSignupResponse', String(error)) };
    }
  }
}

/**
 * Validator for CourseContentFileQuery
 */
export class CourseContentFileQueryValidator extends BaseValidator<CourseContentFileQuery> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "properties": {
    "filename": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Filename"
    }
  },
  "title": "CourseContentFileQuery",
  "type": "object",
  "x-model-name": "CourseContentFileQuery"
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

  validate(data: any): CourseContentFileQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('CourseContentFileQuery', 'Expected an object');
    }

    // Optional field: filename
    if ('filename' in data && data.filename !== undefined && data.filename !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('CourseContentFileQuery', errors.join('; '));
    }

    return data as CourseContentFileQuery;
  }

  safeValidate(data: any): { success: true; data: CourseContentFileQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('CourseContentFileQuery', String(error)) };
    }
  }
}
