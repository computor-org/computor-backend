/**
 * Auto-generated validation classes for Auth models
 * DO NOT EDIT MANUALLY
 */

import type { AuthConfig, BasicAuthConfig, GLPAuthConfig, GradingAuthor, LocalLoginRequest, LocalLoginResponse, LocalTokenRefreshRequest, LocalTokenRefreshResponse, LoginRequest, MessageAuthor, OrganizationUpdateTokenQuery, OrganizationUpdateTokenUpdate, SSOAuthResponse, TokenRefreshRequest, TokenRefreshResponse } from '../generated/auth';
import { BaseValidator, ValidationError } from './BaseValidator';

/**
 * Validator for MessageAuthor
 */
export class MessageAuthorValidator extends BaseValidator<MessageAuthor> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
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
  "type": "object",
  "x-model-name": "MessageAuthor"
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

  validate(data: any): MessageAuthor {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('MessageAuthor', 'Expected an object');
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
      throw new ValidationError('MessageAuthor', errors.join('; '));
    }

    return data as MessageAuthor;
  }

  safeValidate(data: any): { success: true; data: MessageAuthor } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('MessageAuthor', String(error)) };
    }
  }
}

/**
 * Validator for GradingAuthor
 */
export class GradingAuthorValidator extends BaseValidator<GradingAuthor> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
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
  "type": "object",
  "x-model-name": "GradingAuthor"
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

  validate(data: any): GradingAuthor {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('GradingAuthor', 'Expected an object');
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
      throw new ValidationError('GradingAuthor', errors.join('; '));
    }

    return data as GradingAuthor;
  }

  safeValidate(data: any): { success: true; data: GradingAuthor } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('GradingAuthor', String(error)) };
    }
  }
}

/**
 * Validator for AuthConfig
 */
export class AuthConfigValidator extends BaseValidator<AuthConfig> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "properties": {},
  "title": "AuthConfig",
  "type": "object",
  "x-model-name": "AuthConfig"
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

  validate(data: any): AuthConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('AuthConfig', 'Expected an object');
    }

    if (errors.length > 0) {
      throw new ValidationError('AuthConfig', errors.join('; '));
    }

    return data as AuthConfig;
  }

  safeValidate(data: any): { success: true; data: AuthConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('AuthConfig', String(error)) };
    }
  }
}

/**
 * Validator for GLPAuthConfig
 */
export class GLPAuthConfigValidator extends BaseValidator<GLPAuthConfig> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "properties": {
    "url": {
      "title": "Url",
      "type": "string"
    },
    "token": {
      "title": "Token",
      "type": "string"
    }
  },
  "required": [
    "url",
    "token"
  ],
  "title": "GLPAuthConfig",
  "type": "object",
  "x-model-name": "GLPAuthConfig"
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

  validate(data: any): GLPAuthConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('GLPAuthConfig', 'Expected an object');
    }

    // Required field: url
    if (!('url' in data)) {
      errors.push('Missing required field: url');
    } else {
      if (typeof data.url !== 'string') {
        errors.push('Field url must be a string');
      }
    }

    // Required field: token
    if (!('token' in data)) {
      errors.push('Missing required field: token');
    } else {
      if (typeof data.token !== 'string') {
        errors.push('Field token must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('GLPAuthConfig', errors.join('; '));
    }

    return data as GLPAuthConfig;
  }

  safeValidate(data: any): { success: true; data: GLPAuthConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('GLPAuthConfig', String(error)) };
    }
  }
}

/**
 * Validator for BasicAuthConfig
 */
export class BasicAuthConfigValidator extends BaseValidator<BasicAuthConfig> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "properties": {
    "username": {
      "title": "Username",
      "type": "string"
    },
    "password": {
      "title": "Password",
      "type": "string"
    }
  },
  "required": [
    "username",
    "password"
  ],
  "title": "BasicAuthConfig",
  "type": "object",
  "x-model-name": "BasicAuthConfig"
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

  validate(data: any): BasicAuthConfig {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('BasicAuthConfig', 'Expected an object');
    }

    // Required field: username
    if (!('username' in data)) {
      errors.push('Missing required field: username');
    } else {
      if (typeof data.username !== 'string') {
        errors.push('Field username must be a string');
      }
    }

    // Required field: password
    if (!('password' in data)) {
      errors.push('Missing required field: password');
    } else {
      if (typeof data.password !== 'string') {
        errors.push('Field password must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('BasicAuthConfig', errors.join('; '));
    }

    return data as BasicAuthConfig;
  }

  safeValidate(data: any): { success: true; data: BasicAuthConfig } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('BasicAuthConfig', String(error)) };
    }
  }
}

/**
 * Request model for local username/password login.
 */
export class LocalLoginRequestValidator extends BaseValidator<LocalLoginRequest> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "description": "Request model for local username/password login.",
  "properties": {
    "username": {
      "description": "Username or email",
      "minLength": 1,
      "title": "Username",
      "type": "string"
    },
    "password": {
      "description": "Password",
      "minLength": 1,
      "title": "Password",
      "type": "string"
    }
  },
  "required": [
    "username",
    "password"
  ],
  "title": "LocalLoginRequest",
  "type": "object",
  "x-model-name": "LocalLoginRequest"
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

  validate(data: any): LocalLoginRequest {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('LocalLoginRequest', 'Expected an object');
    }

    // Required field: username
    if (!('username' in data)) {
      errors.push('Missing required field: username');
    } else {
      if (typeof data.username !== 'string') {
        errors.push('Field username must be a string');
      }
    }

    // Required field: password
    if (!('password' in data)) {
      errors.push('Missing required field: password');
    } else {
      if (typeof data.password !== 'string') {
        errors.push('Field password must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('LocalLoginRequest', errors.join('; '));
    }

    return data as LocalLoginRequest;
  }

  safeValidate(data: any): { success: true; data: LocalLoginRequest } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('LocalLoginRequest', String(error)) };
    }
  }
}

/**
 * Response model after successful local login.
 */
export class LocalLoginResponseValidator extends BaseValidator<LocalLoginResponse> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "description": "Response model after successful local login.",
  "properties": {
    "access_token": {
      "description": "Bearer access token for API requests",
      "title": "Access Token",
      "type": "string"
    },
    "refresh_token": {
      "description": "Refresh token to obtain new access token",
      "title": "Refresh Token",
      "type": "string"
    },
    "expires_in": {
      "description": "Access token expiration time in seconds",
      "title": "Expires In",
      "type": "integer"
    },
    "user_id": {
      "description": "User ID",
      "title": "User Id",
      "type": "string"
    },
    "token_type": {
      "default": "Bearer",
      "description": "Token type",
      "title": "Token Type",
      "type": "string"
    }
  },
  "required": [
    "access_token",
    "refresh_token",
    "expires_in",
    "user_id"
  ],
  "title": "LocalLoginResponse",
  "type": "object",
  "x-model-name": "LocalLoginResponse"
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

  validate(data: any): LocalLoginResponse {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('LocalLoginResponse', 'Expected an object');
    }

    // Required field: access_token
    if (!('access_token' in data)) {
      errors.push('Missing required field: access_token');
    } else {
      if (typeof data.access_token !== 'string') {
        errors.push('Field access_token must be a string');
      }
    }

    // Required field: refresh_token
    if (!('refresh_token' in data)) {
      errors.push('Missing required field: refresh_token');
    } else {
      if (typeof data.refresh_token !== 'string') {
        errors.push('Field refresh_token must be a string');
      }
    }

    // Required field: expires_in
    if (!('expires_in' in data)) {
      errors.push('Missing required field: expires_in');
    } else {
      if (typeof data.expires_in !== 'number') {
        errors.push('Field expires_in must be a number');
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

    // Optional field: token_type
    if ('token_type' in data && data.token_type !== undefined && data.token_type !== null) {
      if (typeof data.token_type !== 'string') {
        errors.push('Field token_type must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('LocalLoginResponse', errors.join('; '));
    }

    return data as LocalLoginResponse;
  }

  safeValidate(data: any): { success: true; data: LocalLoginResponse } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('LocalLoginResponse', String(error)) };
    }
  }
}

/**
 * Request model for refreshing local session token.
 */
export class LocalTokenRefreshRequestValidator extends BaseValidator<LocalTokenRefreshRequest> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "description": "Request model for refreshing local session token.",
  "properties": {
    "refresh_token": {
      "description": "Refresh token from initial authentication",
      "title": "Refresh Token",
      "type": "string"
    }
  },
  "required": [
    "refresh_token"
  ],
  "title": "LocalTokenRefreshRequest",
  "type": "object",
  "x-model-name": "LocalTokenRefreshRequest"
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

  validate(data: any): LocalTokenRefreshRequest {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('LocalTokenRefreshRequest', 'Expected an object');
    }

    // Required field: refresh_token
    if (!('refresh_token' in data)) {
      errors.push('Missing required field: refresh_token');
    } else {
      if (typeof data.refresh_token !== 'string') {
        errors.push('Field refresh_token must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('LocalTokenRefreshRequest', errors.join('; '));
    }

    return data as LocalTokenRefreshRequest;
  }

  safeValidate(data: any): { success: true; data: LocalTokenRefreshRequest } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('LocalTokenRefreshRequest', String(error)) };
    }
  }
}

/**
 * Response model after successful token refresh.
 */
export class LocalTokenRefreshResponseValidator extends BaseValidator<LocalTokenRefreshResponse> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "description": "Response model after successful token refresh.",
  "properties": {
    "access_token": {
      "description": "New Bearer access token",
      "title": "Access Token",
      "type": "string"
    },
    "expires_in": {
      "description": "Token expiration time in seconds",
      "title": "Expires In",
      "type": "integer"
    },
    "refresh_token": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "New refresh token if rotated",
      "title": "Refresh Token"
    },
    "token_type": {
      "default": "Bearer",
      "description": "Token type",
      "title": "Token Type",
      "type": "string"
    }
  },
  "required": [
    "access_token",
    "expires_in"
  ],
  "title": "LocalTokenRefreshResponse",
  "type": "object",
  "x-model-name": "LocalTokenRefreshResponse"
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

  validate(data: any): LocalTokenRefreshResponse {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('LocalTokenRefreshResponse', 'Expected an object');
    }

    // Required field: access_token
    if (!('access_token' in data)) {
      errors.push('Missing required field: access_token');
    } else {
      if (typeof data.access_token !== 'string') {
        errors.push('Field access_token must be a string');
      }
    }

    // Required field: expires_in
    if (!('expires_in' in data)) {
      errors.push('Missing required field: expires_in');
    } else {
      if (typeof data.expires_in !== 'number') {
        errors.push('Field expires_in must be a number');
      }
    }

    // Optional field: refresh_token
    if ('refresh_token' in data && data.refresh_token !== undefined && data.refresh_token !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: token_type
    if ('token_type' in data && data.token_type !== undefined && data.token_type !== null) {
      if (typeof data.token_type !== 'string') {
        errors.push('Field token_type must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('LocalTokenRefreshResponse', errors.join('; '));
    }

    return data as LocalTokenRefreshResponse;
  }

  safeValidate(data: any): { success: true; data: LocalTokenRefreshResponse } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('LocalTokenRefreshResponse', String(error)) };
    }
  }
}

/**
 * Validator for OrganizationUpdateTokenQuery
 */
export class OrganizationUpdateTokenQueryValidator extends BaseValidator<OrganizationUpdateTokenQuery> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "properties": {
    "type": {
      "title": "Type",
      "type": "string"
    }
  },
  "required": [
    "type"
  ],
  "title": "OrganizationUpdateTokenQuery",
  "type": "object",
  "x-model-name": "OrganizationUpdateTokenQuery"
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

  validate(data: any): OrganizationUpdateTokenQuery {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('OrganizationUpdateTokenQuery', 'Expected an object');
    }

    // Required field: type
    if (!('type' in data)) {
      errors.push('Missing required field: type');
    } else {
      if (typeof data.type !== 'string') {
        errors.push('Field type must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('OrganizationUpdateTokenQuery', errors.join('; '));
    }

    return data as OrganizationUpdateTokenQuery;
  }

  safeValidate(data: any): { success: true; data: OrganizationUpdateTokenQuery } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('OrganizationUpdateTokenQuery', String(error)) };
    }
  }
}

/**
 * Validator for OrganizationUpdateTokenUpdate
 */
export class OrganizationUpdateTokenUpdateValidator extends BaseValidator<OrganizationUpdateTokenUpdate> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "properties": {
    "token": {
      "title": "Token",
      "type": "string"
    }
  },
  "required": [
    "token"
  ],
  "title": "OrganizationUpdateTokenUpdate",
  "type": "object",
  "x-model-name": "OrganizationUpdateTokenUpdate"
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

  validate(data: any): OrganizationUpdateTokenUpdate {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('OrganizationUpdateTokenUpdate', 'Expected an object');
    }

    // Required field: token
    if (!('token' in data)) {
      errors.push('Missing required field: token');
    } else {
      if (typeof data.token !== 'string') {
        errors.push('Field token must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('OrganizationUpdateTokenUpdate', errors.join('; '));
    }

    return data as OrganizationUpdateTokenUpdate;
  }

  safeValidate(data: any): { success: true; data: OrganizationUpdateTokenUpdate } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('OrganizationUpdateTokenUpdate', String(error)) };
    }
  }
}

/**
 * Login request for SSO.
 */
export class LoginRequestValidator extends BaseValidator<LoginRequest> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "description": "Login request for SSO.",
  "properties": {
    "provider": {
      "description": "Provider name",
      "title": "Provider",
      "type": "string"
    },
    "redirect_uri": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Redirect URI after login",
      "title": "Redirect Uri"
    }
  },
  "required": [
    "provider"
  ],
  "title": "LoginRequest",
  "type": "object",
  "x-model-name": "LoginRequest"
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

  validate(data: any): LoginRequest {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('LoginRequest', 'Expected an object');
    }

    // Required field: provider
    if (!('provider' in data)) {
      errors.push('Missing required field: provider');
    } else {
      if (typeof data.provider !== 'string') {
        errors.push('Field provider must be a string');
      }
    }

    // Optional field: redirect_uri
    if ('redirect_uri' in data && data.redirect_uri !== undefined && data.redirect_uri !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('LoginRequest', errors.join('; '));
    }

    return data as LoginRequest;
  }

  safeValidate(data: any): { success: true; data: LoginRequest } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('LoginRequest', String(error)) };
    }
  }
}

/**
 * Response after successful SSO authentication.
 */
export class SSOAuthResponseValidator extends BaseValidator<SSOAuthResponse> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "description": "Response after successful SSO authentication.",
  "properties": {
    "user_id": {
      "description": "User ID",
      "title": "User Id",
      "type": "string"
    },
    "account_id": {
      "description": "Account ID",
      "title": "Account Id",
      "type": "string"
    },
    "access_token": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Access token if available",
      "title": "Access Token"
    },
    "is_new_user": {
      "description": "Whether this is a new user",
      "title": "Is New User",
      "type": "boolean"
    }
  },
  "required": [
    "user_id",
    "account_id",
    "is_new_user"
  ],
  "title": "SSOAuthResponse",
  "type": "object",
  "x-model-name": "SSOAuthResponse"
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

  validate(data: any): SSOAuthResponse {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('SSOAuthResponse', 'Expected an object');
    }

    // Required field: user_id
    if (!('user_id' in data)) {
      errors.push('Missing required field: user_id');
    } else {
      if (typeof data.user_id !== 'string') {
        errors.push('Field user_id must be a string');
      }
    }

    // Required field: account_id
    if (!('account_id' in data)) {
      errors.push('Missing required field: account_id');
    } else {
      if (typeof data.account_id !== 'string') {
        errors.push('Field account_id must be a string');
      }
    }

    // Optional field: access_token
    if ('access_token' in data && data.access_token !== undefined && data.access_token !== null) {
      // Union type - skipping detailed validation
    }

    // Required field: is_new_user
    if (!('is_new_user' in data)) {
      errors.push('Missing required field: is_new_user');
    } else {
      if (typeof data.is_new_user !== 'boolean') {
        errors.push('Field is_new_user must be a boolean');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('SSOAuthResponse', errors.join('; '));
    }

    return data as SSOAuthResponse;
  }

  safeValidate(data: any): { success: true; data: SSOAuthResponse } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('SSOAuthResponse', String(error)) };
    }
  }
}

/**
 * Token refresh request.
 */
export class TokenRefreshRequestValidator extends BaseValidator<TokenRefreshRequest> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "description": "Token refresh request.",
  "properties": {
    "refresh_token": {
      "description": "Refresh token from initial authentication",
      "title": "Refresh Token",
      "type": "string"
    },
    "provider": {
      "default": "keycloak",
      "description": "Authentication provider",
      "title": "Provider",
      "type": "string"
    }
  },
  "required": [
    "refresh_token"
  ],
  "title": "TokenRefreshRequest",
  "type": "object",
  "x-model-name": "TokenRefreshRequest"
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

  validate(data: any): TokenRefreshRequest {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('TokenRefreshRequest', 'Expected an object');
    }

    // Required field: refresh_token
    if (!('refresh_token' in data)) {
      errors.push('Missing required field: refresh_token');
    } else {
      if (typeof data.refresh_token !== 'string') {
        errors.push('Field refresh_token must be a string');
      }
    }

    // Optional field: provider
    if ('provider' in data && data.provider !== undefined && data.provider !== null) {
      if (typeof data.provider !== 'string') {
        errors.push('Field provider must be a string');
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('TokenRefreshRequest', errors.join('; '));
    }

    return data as TokenRefreshRequest;
  }

  safeValidate(data: any): { success: true; data: TokenRefreshRequest } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('TokenRefreshRequest', String(error)) };
    }
  }
}

/**
 * Response after successful token refresh.
 */
export class TokenRefreshResponseValidator extends BaseValidator<TokenRefreshResponse> {
  /**
   * JSON Schema for this model
   * Useful for form generation, validation, and documentation
   */
  static readonly schema = JSON.parse(`{
  "description": "Response after successful token refresh.",
  "properties": {
    "access_token": {
      "description": "New access token",
      "title": "Access Token",
      "type": "string"
    },
    "expires_in": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Token expiration time in seconds",
      "title": "Expires In"
    },
    "refresh_token": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "New refresh token if rotated",
      "title": "Refresh Token"
    }
  },
  "required": [
    "access_token"
  ],
  "title": "TokenRefreshResponse",
  "type": "object",
  "x-model-name": "TokenRefreshResponse"
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

  validate(data: any): TokenRefreshResponse {
    const errors: string[] = [];

    if (typeof data !== 'object' || data === null) {
      throw new ValidationError('TokenRefreshResponse', 'Expected an object');
    }

    // Required field: access_token
    if (!('access_token' in data)) {
      errors.push('Missing required field: access_token');
    } else {
      if (typeof data.access_token !== 'string') {
        errors.push('Field access_token must be a string');
      }
    }

    // Optional field: expires_in
    if ('expires_in' in data && data.expires_in !== undefined && data.expires_in !== null) {
      // Union type - skipping detailed validation
    }

    // Optional field: refresh_token
    if ('refresh_token' in data && data.refresh_token !== undefined && data.refresh_token !== null) {
      // Union type - skipping detailed validation
    }

    if (errors.length > 0) {
      throw new ValidationError('TokenRefreshResponse', errors.join('; '));
    }

    return data as TokenRefreshResponse;
  }

  safeValidate(data: any): { success: true; data: TokenRefreshResponse } | { success: false; error: ValidationError } {
    try {
      const validData = this.validate(data);
      return { success: true, data: validData };
    } catch (error) {
      if (error instanceof ValidationError) {
        return { success: false, error };
      }
      return { success: false, error: new ValidationError('TokenRefreshResponse', String(error)) };
    }
  }
}
