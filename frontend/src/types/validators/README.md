# TypeScript Validation Classes

**Auto-generated runtime validators for Pydantic models**

🚨 **DO NOT EDIT FILES IN THIS DIRECTORY MANUALLY** - They are auto-generated and will be overwritten.

## What is this?

This directory contains TypeScript validation classes that validate API response data at runtime. Each validator corresponds to a Pydantic model from the backend.

## Quick Start

```typescript
import { UserGetValidator, ValidationError } from 'types/validators';

// Validate API response
const validator = new UserGetValidator();

try {
  const validatedUser = validator.validate(apiResponseData);
  // validatedUser is now type-safe and validated ✅
  console.log(validatedUser.email);
} catch (error) {
  if (error instanceof ValidationError) {
    console.error('Invalid data:', error.validationMessage);
  }
}
```

## Files in this Directory

- **BaseValidator.ts** - Base validation class with error handling
- **auth.validators.ts** - Authentication model validators
- **users.validators.ts** - User model validators
- **courses.validators.ts** - Course model validators
- **organizations.validators.ts** - Organization model validators
- **common.validators.ts** - Shared/common model validators
- **index.ts** - Barrel exports for convenient imports

## Regeneration

When backend Pydantic models change, regenerate validators:

```bash
# From project root
bash generate_validators.sh
```

This will:
1. Export JSON schemas from Pydantic models
2. Generate new TypeScript validator classes
3. Update this directory

## Validation Methods

Each validator class provides:

### `validate(data: any): T`
Validates data and returns typed instance. **Throws** `ValidationError` on failure.

```typescript
const user = validator.validate(data); // throws on error
```

### `safeValidate(data: any): Result<T>`
Validates data without throwing. Returns success/failure result object.

```typescript
const result = validator.safeValidate(data);
if (result.success) {
  console.log(result.data);
} else {
  console.error(result.error);
}
```

### `validateArray(data: any[]): T[]`
Validates an array of items. Throws with context on which item failed.

```typescript
const users = validator.validateArray(arrayData);
```

## Examples

See [validatedClient.example.ts](../../api/validatedClient.example.ts) for:
- Wrapper clients with automatic validation
- React hooks with validation
- Conditional validation
- Error handling patterns
- And more...

## Documentation

Full documentation: [docs/typescript-validation.md](../../../../docs/typescript-validation.md)

## Error Handling

```typescript
import { ValidationError } from 'types/validators';

try {
  const data = validator.validate(apiData);
} catch (error) {
  if (error instanceof ValidationError) {
    console.error('Validation failed:', {
      model: error.modelName,      // e.g., "UserGet"
      message: error.validationMessage  // e.g., "Missing required field: email"
    });
  }
}
```

## Best Practices

✅ **DO:**
- Validate at API boundaries (when data enters your app)
- Use `safeValidate()` for non-critical paths
- Log validation failures (they indicate contract issues)
- Regenerate after backend model changes

❌ **DON'T:**
- Edit generated files manually
- Validate data repeatedly
- Use validation for business logic
- Validate in every component render

## Integration with Generated Types

Validators work alongside generated TypeScript interfaces:

```typescript
import { UserGet } from 'types/generated/users';        // Type definition
import { UserGetValidator } from 'types/validators';    // Runtime validator

const validator = new UserGetValidator();
const user: UserGet = validator.validate(apiData);
// Both type-safe AND runtime-validated ✅
```

## Need Help?

- [Full Documentation](../../../../docs/typescript-validation.md)
- [Usage Examples](../../api/validatedClient.example.ts)
- [Architecture Overview](../../../../docs/architecture-overview.md)