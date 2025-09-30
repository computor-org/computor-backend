/**
 * Base validator class with error handling
 * DO NOT EDIT MANUALLY
 */

export class ValidationError extends Error {
  constructor(
    public readonly modelName: string,
    public readonly validationMessage: string
  ) {
    super(`Validation failed for ${modelName}: ${validationMessage}`);
    this.name = 'ValidationError';
  }
}

export abstract class BaseValidator<T> {
  /**
   * Validate data and return typed instance
   * @throws ValidationError if validation fails
   */
  abstract validate(data: any): T;

  /**
   * Safe validation that returns result object instead of throwing
   */
  abstract safeValidate(data: any): { success: true; data: T } | { success: false; error: ValidationError };

  /**
   * Validate array of items
   */
  validateArray(data: any[]): T[] {
    return data.map((item, index) => {
      try {
        return this.validate(item);
      } catch (error) {
        if (error instanceof ValidationError) {
          throw new ValidationError(
            error.modelName,
            `Item at index ${index}: ${error.validationMessage}`
          );
        }
        throw error;
      }
    });
  }
}
