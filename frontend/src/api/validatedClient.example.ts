/**
 * Example: How to integrate validation classes with generated API clients
 *
 * This file demonstrates best practices for adding runtime validation
 * to your API client calls.
 */

import { CourseClient, UserClient } from './generated';
import {
  CourseGetValidator,
  CourseListValidator,
  UserGetValidator,
  UserListValidator,
  ValidationError
} from '../types/validators';

// ============================================================================
// Pattern 1: Wrapper Client with Automatic Validation
// ============================================================================

/**
 * Extends generated client to add automatic validation
 */
export class ValidatedCourseClient extends CourseClient {
  private getValidator = new CourseGetValidator();
  private listValidator = new CourseListValidator();

  /**
   * Override get() to add validation
   */
  async get(id: string | number) {
    try {
      const data = await super.get(id);
      return this.getValidator.validate(data);
    } catch (error) {
      if (error instanceof ValidationError) {
        console.error(`[ValidatedCourseClient] Validation failed for course ${id}:`, error.validationMessage);
        throw new Error(`Invalid course data received from server: ${error.validationMessage}`);
      }
      throw error;
    }
  }

  /**
   * Override list() to add array validation
   */
  async list(params?: any) {
    try {
      const data = await super.list(params);
      return this.listValidator.validateArray(data);
    } catch (error) {
      if (error instanceof ValidationError) {
        console.error('[ValidatedCourseClient] Validation failed for course list:', error.validationMessage);
        throw new Error(`Invalid course list data received from server: ${error.validationMessage}`);
      }
      throw error;
    }
  }
}

// ============================================================================
// Pattern 2: Validation Decorator/Wrapper Function
// ============================================================================

/**
 * Generic validator wrapper for any async function
 */
export function withValidation<T, TValidator extends { validate(data: any): T }>(
  apiCall: () => Promise<any>,
  validator: TValidator,
  errorContext?: string
): Promise<T> {
  return apiCall().then(data => {
    try {
      return validator.validate(data);
    } catch (error) {
      if (error instanceof ValidationError) {
        const context = errorContext ? `[${errorContext}] ` : '';
        console.error(`${context}Validation failed:`, error.validationMessage);
        throw new Error(`Invalid data from API: ${error.validationMessage}`);
      }
      throw error;
    }
  });
}

/**
 * Usage example with validator wrapper
 */
export async function fetchValidatedCourse(id: string) {
  const client = new CourseClient();
  const validator = new CourseGetValidator();

  return withValidation(
    () => client.get(id),
    validator,
    'fetchValidatedCourse'
  );
}

// ============================================================================
// Pattern 3: Safe Validation (No Exceptions)
// ============================================================================

/**
 * Type for safe validation results
 */
export type SafeResult<T> =
  | { success: true; data: T }
  | { success: false; error: string };

/**
 * Fetch with safe validation (returns result instead of throwing)
 */
export async function safeFetchCourse(id: string): Promise<SafeResult<any>> {
  try {
    const client = new CourseClient();
    const data = await client.get(id);

    const validator = new CourseGetValidator();
    const result = validator.safeValidate(data);

    if (result.success) {
      return { success: true, data: result.data };
    } else {
      return {
        success: false,
        error: `Validation failed: ${result.error.validationMessage}`
      };
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}

// ============================================================================
// Pattern 4: Conditional/Development-Only Validation
// ============================================================================

/**
 * Validates only in development mode
 */
export class ConditionalValidationClient extends UserClient {
  private getValidator = new UserGetValidator();
  private listValidator = new UserListValidator();

  async get(id: string | number) {
    const data = await super.get(id);

    // Only validate in development
    if (process.env.NODE_ENV === 'development') {
      const result = this.getValidator.safeValidate(data);
      if (!result.success) {
        console.warn('[DEV] User validation failed:', result.error.validationMessage);
        // In dev, we log but don't throw - helps catch issues during development
      }
    }

    return data;
  }

  async list(params?: any) {
    const data = await super.list(params);

    if (process.env.NODE_ENV === 'development') {
      try {
        return this.listValidator.validateArray(data);
      } catch (error) {
        if (error instanceof ValidationError) {
          console.warn('[DEV] User list validation failed:', error.validationMessage);
        }
        // Return unvalidated data in dev mode
        return data;
      }
    }

    return data;
  }
}

// ============================================================================
// Pattern 5: React Hook with Validation
// ============================================================================

/**
 * Example React hook that validates API responses
 */
import { useState, useEffect } from 'react';

export function useValidatedCourse(id: string) {
  const [course, setCourse] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCourse = async () => {
      setLoading(true);
      setError(null);

      try {
        const client = new CourseClient();
        const data = await client.get(id);

        const validator = new CourseGetValidator();
        const validatedCourse = validator.validate(data);

        setCourse(validatedCourse);
      } catch (err) {
        if (err instanceof ValidationError) {
          setError(`Data validation error: ${err.validationMessage}`);
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('An unknown error occurred');
        }
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchCourse();
    }
  }, [id]);

  return { course, error, loading };
}

// ============================================================================
// Pattern 6: Batch Validation
// ============================================================================

/**
 * Validate multiple items and collect all errors
 */
export function validateBatch<T>(
  items: any[],
  validator: { validate(data: any): T },
  options?: { stopOnError?: boolean }
): { valid: T[]; errors: Array<{ index: number; error: string }> } {
  const valid: T[] = [];
  const errors: Array<{ index: number; error: string }> = [];

  for (let i = 0; i < items.length; i++) {
    try {
      const validated = validator.validate(items[i]);
      valid.push(validated);
    } catch (error) {
      if (error instanceof ValidationError) {
        errors.push({ index: i, error: error.validationMessage });
        if (options?.stopOnError) {
          break;
        }
      }
    }
  }

  return { valid, errors };
}

// Usage:
export async function fetchAndValidateAllCourses() {
  const client = new CourseClient();
  const data = await client.list();

  const validator = new CourseListValidator();
  const result = validateBatch(data, validator);

  if (result.errors.length > 0) {
    console.warn(`Validation failed for ${result.errors.length} courses:`, result.errors);
  }

  return result.valid; // Return only valid courses
}

// ============================================================================
// Pattern 7: Logging and Monitoring
// ============================================================================

/**
 * Validation with structured logging
 */
export async function fetchCourseWithLogging(id: string) {
  const startTime = performance.now();
  const client = new CourseClient();
  const validator = new CourseGetValidator();

  try {
    const data = await client.get(id);
    const validationStartTime = performance.now();

    const validated = validator.validate(data);

    const validationDuration = performance.now() - validationStartTime;
    const totalDuration = performance.now() - startTime;

    console.log('[API Metrics]', {
      endpoint: 'course.get',
      courseId: id,
      totalDuration: `${totalDuration.toFixed(2)}ms`,
      validationDuration: `${validationDuration.toFixed(2)}ms`,
      validationOverhead: `${((validationDuration / totalDuration) * 100).toFixed(1)}%`,
      validated: true,
    });

    return validated;
  } catch (error) {
    const totalDuration = performance.now() - startTime;

    if (error instanceof ValidationError) {
      console.error('[API Error]', {
        endpoint: 'course.get',
        courseId: id,
        totalDuration: `${totalDuration.toFixed(2)}ms`,
        errorType: 'ValidationError',
        errorMessage: error.validationMessage,
      });
    }

    throw error;
  }
}

// ============================================================================
// Best Practices Summary
// ============================================================================

/*
1. Choose the right pattern:
   - Pattern 1 (Wrapper Client): Best for consistent validation across app
   - Pattern 2 (Wrapper Function): Best for one-off validations
   - Pattern 3 (Safe Validation): Best for graceful error handling
   - Pattern 4 (Conditional): Best for development-time validation
   - Pattern 5 (React Hook): Best for component-level data fetching
   - Pattern 6 (Batch): Best for validating collections
   - Pattern 7 (Logging): Best for monitoring and debugging

2. Where to validate:
   ✅ At API boundaries (when data enters your app)
   ✅ In shared API client wrappers
   ✅ In data fetching hooks
   ❌ In UI components (validate once, not every render)
   ❌ In business logic (data should already be validated)

3. Error handling:
   - Log validation failures (they indicate contract issues)
   - Provide helpful error messages to users
   - Consider graceful degradation for non-critical data
   - Monitor validation errors in production

4. Performance:
   - Validation overhead is minimal (<1ms per call)
   - Consider conditional validation in production
   - Don't validate the same data multiple times
   - Use safeValidate() to avoid exception overhead

5. Development workflow:
   - Regenerate validators when backend models change
   - Add custom validators for business logic
   - Test validation with malformed data
   - Use TypeScript types + runtime validation together
*/