/**
 * Auto-generated validation classes for Tasks models
 * DO NOT EDIT MANUALLY
 */

import type { TaskInfo, TaskResponse, TaskResult, TaskSubmission, TestJob } from '../generated/tasks';
import { TaskStatus } from '../generated/tasks';
import { BaseValidator, ValidationError } from './BaseValidator';

export function validateTaskStatus(value: any): TaskStatus {
  const validValues = ['queued', 'started', 'finished', 'failed', 'deferred', 'cancelled'];
  if (!validValues.includes(value)) {
    throw new ValidationError('TaskStatus', `Invalid value: ${value}. Expected one of: ${validValues.join(', ')}`);
  }
  return value as TaskStatus;
}

/**
 * Validator for TestJob
 */
export class TestJobValidator extends BaseValidator<TestJob> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
    "Repository": {
      "properties": {
        "url": {
          "title": "Url",
          "type": "string"
        },
        "user": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": "",
          "title": "User"
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
          "default": "",
          "title": "Token"
        },
        "branch": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": "main",
          "title": "Branch"
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
          "default": "",
          "title": "Path"
        },
        "commit": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": "",
          "title": "Commit"
        }
      },
      "required": [
        "url"
      ],
      "title": "Repository",
      "type": "object"
    }
  },
  "properties": {
    "user_id": {
      "title": "User Id",
      "type": "string"
    },
    "course_member_id": {
      "title": "Course Member Id",
      "type": "string"
    },
    "course_content_id": {
      "title": "Course Content Id",
      "type": "string"
    },
    "execution_backend_id": {
      "title": "Execution Backend Id",
      "type": "string"
    },
    "execution_backend_type": {
      "title": "Execution Backend Type",
      "type": "string"
    },
    "module": {
      "$ref": "#/$defs/Repository"
    },
    "reference": {
      "anyOf": [
        {
          "$ref": "#/$defs/Repository"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "test_number": {
      "default": -1,
      "title": "Test Number",
      "type": "integer"
    },
    "submission_number": {
      "default": -1,
      "title": "Submission Number",
      "type": "integer"
    }
  },
  "required": [
    "user_id",
    "course_member_id",
    "course_content_id",
    "execution_backend_id",
    "execution_backend_type",
    "module"
  ],
  "title": "TestJob",
  "type": "object",
  "x-model-name": "TestJob"
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

  validate(data: any): TestJob {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('TestJob', 'Expected an object');
    }

    // Required field: user_id
    if (!('user_id' in data)) {
      errors.push('Missing required field: user_id');
    } else {
      if (typeof data.user_id !== 'string') {
        errors.push('Field user_id must be a string');
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

    // Required field: course_content_id
    if (!('course_content_id' in data)) {
      errors.push('Missing required field: course_content_id');
    } else {
      if (typeof data.course_content_id !== 'string') {
        errors.push('Field course_content_id must be a string');
      }
    }

    // Required field: execution_backend_id
    if (!('execution_backend_id' in data)) {
      errors.push('Missing required field: execution_backend_id');
    } else {
      if (typeof data.execution_backend_id !== 'string') {
        errors.push('Field execution_backend_id must be a string');
      }
    }

    // Required field: execution_backend_type
    if (!('execution_backend_type' in data)) {
      errors.push('Missing required field: execution_backend_type');
    } else {
      if (typeof data.execution_backend_type !== 'string') {
        errors.push('Field execution_backend_type must be a string');
      }
    }

    // Required field: module
    if (!('module' in data)) {
      errors.push('Missing required field: module');
    } else {
      // Reference field - basic object check
      if (typeof data.module !== 'object') {
        errors.push('Field module must be an object');
      }
    }

    // Optional field: reference
    if ('reference' in data && data.reference !== undefined && data.reference !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: test_number
    if ('test_number' in data && data.test_number !== undefined && data.test_number !== null) {
      if (typeof data.test_number !== 'number') {
        errors.push('Field test_number must be a number');
      }
    }

    // Optional field: submission_number
    if ('submission_number' in data && data.submission_number !== undefined && data.submission_number !== null) {
      if (typeof data.submission_number !== 'number') {
        errors.push('Field submission_number must be a number');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('TestJob', errors.join('; '));
    }

    return data as TestJob;
  }

  safeValidate(data: any): { success: true; data: TestJob } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('TestJob', String(error)) };
    }
  }
}

/**
 * Response with task ID for async operation.
 */
export class TaskResponseValidator extends BaseValidator<TaskResponse> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Response with task ID for async operation.",
  "properties": {
    "task_id": {
      "title": "Task Id",
      "type": "string"
    },
    "status": {
      "title": "Status",
      "type": "string"
    },
    "message": {
      "title": "Message",
      "type": "string"
    }
  },
  "required": [
    "task_id",
    "status",
    "message"
  ],
  "title": "TaskResponse",
  "type": "object",
  "x-model-name": "TaskResponse"
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

  validate(data: any): TaskResponse {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('TaskResponse', 'Expected an object');
    }

    // Required field: task_id
    if (!('task_id' in data)) {
      errors.push('Missing required field: task_id');
    } else {
      if (typeof data.task_id !== 'string') {
        errors.push('Field task_id must be a string');
      }
    }

    // Required field: status
    if (!('status' in data)) {
      errors.push('Missing required field: status');
    } else {
      if (typeof data.status !== 'string') {
        errors.push('Field status must be a string');
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
      throw new ValidationError('TaskResponse', errors.join('; '));
    }

    return data as TaskResponse;
  }

  safeValidate(data: any): { success: true; data: TaskResponse } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('TaskResponse', String(error)) };
    }
  }
}

/**
 * Task execution result container.
 */
export class TaskResultValidator extends BaseValidator<TaskResult> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
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
  "description": "Task execution result container.",
  "properties": {
    "task_id": {
      "title": "Task Id",
      "type": "string"
    },
    "status": {
      "$ref": "#/$defs/TaskStatus"
    },
    "result": {
      "anyOf": [
        {},
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Result"
    },
    "error": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Error"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "started_at": {
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
      "title": "Started At"
    },
    "finished_at": {
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
      "title": "Finished At"
    },
    "progress": {
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
      "title": "Progress"
    }
  },
  "required": [
    "task_id",
    "status",
    "created_at"
  ],
  "title": "TaskResult",
  "type": "object",
  "x-model-name": "TaskResult"
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

  validate(data: any): TaskResult {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('TaskResult', 'Expected an object');
    }

    // Required field: task_id
    if (!('task_id' in data)) {
      errors.push('Missing required field: task_id');
    } else {
      if (typeof data.task_id !== 'string') {
        errors.push('Field task_id must be a string');
      }
    }

    // Required field: status
    if (!('status' in data)) {
      errors.push('Missing required field: status');
    } else {
      // Reference field - basic object check
      if (typeof data.status !== 'object') {
        errors.push('Field status must be an object');
      }
    }

    // Optional field: result
    if ('result' in data && data.result !== undefined && data.result !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: error
    if ('error' in data && data.error !== undefined && data.error !== null) {
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

    // Optional field: started_at
    if ('started_at' in data && data.started_at !== undefined && data.started_at !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: finished_at
    if ('finished_at' in data && data.finished_at !== undefined && data.finished_at !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: progress
    if ('progress' in data && data.progress !== undefined && data.progress !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('TaskResult', errors.join('; '));
    }

    return data as TaskResult;
  }

  safeValidate(data: any): { success: true; data: TaskResult } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('TaskResult', String(error)) };
    }
  }
}

/**
 * Task submission request.
 */
export class TaskSubmissionValidator extends BaseValidator<TaskSubmission> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "description": "Task submission request.",
  "properties": {
    "task_name": {
      "title": "Task Name",
      "type": "string"
    },
    "parameters": {
      "additionalProperties": true,
      "default": {},
      "title": "Parameters",
      "type": "object"
    },
    "queue": {
      "default": "computor-tasks",
      "title": "Queue",
      "type": "string"
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
      "default": null,
      "title": "Workflow Id"
    },
    "delay": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Delay"
    }
  },
  "required": [
    "task_name"
  ],
  "title": "TaskSubmission",
  "type": "object",
  "x-model-name": "TaskSubmission"
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

  validate(data: any): TaskSubmission {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('TaskSubmission', 'Expected an object');
    }

    // Required field: task_name
    if (!('task_name' in data)) {
      errors.push('Missing required field: task_name');
    } else {
      if (typeof data.task_name !== 'string') {
        errors.push('Field task_name must be a string');
      }
    }

    // Optional field: parameters
    if ('parameters' in data && data.parameters !== undefined && data.parameters !== null) {
      if (typeof data.parameters !== 'object' || data.parameters === null) {
        errors.push('Field parameters must be an object');
      }
    }

    // Optional field: queue
    if ('queue' in data && data.queue !== undefined && data.queue !== null) {
      if (typeof data.queue !== 'string') {
        errors.push('Field queue must be a string');
      }
    }

    // Optional field: workflow_id
    if ('workflow_id' in data && data.workflow_id !== undefined && data.workflow_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: delay
    if ('delay' in data && data.delay !== undefined && data.delay !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('TaskSubmission', errors.join('; '));
    }

    return data as TaskSubmission;
  }

  safeValidate(data: any): { success: true; data: TaskSubmission } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('TaskSubmission', String(error)) };
    }
  }
}

/**
 * Task information for status queries.
 */
export class TaskInfoValidator extends BaseValidator<TaskInfo> {
  private static _schema: any = null;

  /**
   * Get JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static getSchema(): any {
    if (!this._schema) {
      this._schema = JSON.parse(`{
  "$defs": {
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
  "description": "Task information for status queries.",
  "properties": {
    "task_id": {
      "title": "Task Id",
      "type": "string"
    },
    "task_name": {
      "title": "Task Name",
      "type": "string"
    },
    "status": {
      "$ref": "#/$defs/TaskStatus"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "started_at": {
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
      "title": "Started At"
    },
    "finished_at": {
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
      "title": "Finished At"
    },
    "progress": {
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
      "title": "Progress"
    },
    "error": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Error"
    },
    "worker": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Worker"
    },
    "queue": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Queue"
    },
    "retries": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Retries"
    },
    "args": {
      "anyOf": [
        {},
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Args"
    },
    "kwargs": {
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
      "title": "Kwargs"
    },
    "short_task_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Short Task Id"
    },
    "status_display": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Status Display"
    },
    "completed_at": {
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
      "title": "Completed At"
    },
    "has_result": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Has Result"
    },
    "result_available": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Result Available"
    },
    "duration": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Duration"
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
      "default": null,
      "title": "Workflow Id"
    },
    "run_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Run Id"
    },
    "execution_time": {
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
      "title": "Execution Time"
    },
    "history_length": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "History Length"
    }
  },
  "required": [
    "task_id",
    "task_name",
    "status",
    "created_at"
  ],
  "title": "TaskInfo",
  "type": "object",
  "x-model-name": "TaskInfo"
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

  validate(data: any): TaskInfo {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('TaskInfo', 'Expected an object');
    }

    // Required field: task_id
    if (!('task_id' in data)) {
      errors.push('Missing required field: task_id');
    } else {
      if (typeof data.task_id !== 'string') {
        errors.push('Field task_id must be a string');
      }
    }

    // Required field: task_name
    if (!('task_name' in data)) {
      errors.push('Missing required field: task_name');
    } else {
      if (typeof data.task_name !== 'string') {
        errors.push('Field task_name must be a string');
      }
    }

    // Required field: status
    if (!('status' in data)) {
      errors.push('Missing required field: status');
    } else {
      // Reference field - basic object check
      if (typeof data.status !== 'object') {
        errors.push('Field status must be an object');
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

    // Optional field: started_at
    if ('started_at' in data && data.started_at !== undefined && data.started_at !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: finished_at
    if ('finished_at' in data && data.finished_at !== undefined && data.finished_at !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: progress
    if ('progress' in data && data.progress !== undefined && data.progress !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: error
    if ('error' in data && data.error !== undefined && data.error !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: worker
    if ('worker' in data && data.worker !== undefined && data.worker !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: queue
    if ('queue' in data && data.queue !== undefined && data.queue !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: retries
    if ('retries' in data && data.retries !== undefined && data.retries !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: args
    if ('args' in data && data.args !== undefined && data.args !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: kwargs
    if ('kwargs' in data && data.kwargs !== undefined && data.kwargs !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: short_task_id
    if ('short_task_id' in data && data.short_task_id !== undefined && data.short_task_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: status_display
    if ('status_display' in data && data.status_display !== undefined && data.status_display !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: completed_at
    if ('completed_at' in data && data.completed_at !== undefined && data.completed_at !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: has_result
    if ('has_result' in data && data.has_result !== undefined && data.has_result !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: result_available
    if ('result_available' in data && data.result_available !== undefined && data.result_available !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: duration
    if ('duration' in data && data.duration !== undefined && data.duration !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: workflow_id
    if ('workflow_id' in data && data.workflow_id !== undefined && data.workflow_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: run_id
    if ('run_id' in data && data.run_id !== undefined && data.run_id !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: execution_time
    if ('execution_time' in data && data.execution_time !== undefined && data.execution_time !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: history_length
    if ('history_length' in data && data.history_length !== undefined && data.history_length !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('TaskInfo', errors.join('; '));
    }

    return data as TaskInfo;
  }

  safeValidate(data: any): { success: true; data: TaskInfo } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('TaskInfo', String(error)) };
    }
  }
}
