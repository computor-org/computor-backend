/**
 * Utilities for generating forms from JSON Schema
 * Works with validator classes that have static schema property
 */

// Type for JSON Schema property definition
export interface SchemaProperty {
  type?: string | string[];
  title?: string;
  description?: string;
  default?: any;
  enum?: any[];
  format?: string;
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  anyOf?: any[];
  oneOf?: any[];
  allOf?: any[];
  properties?: Record<string, SchemaProperty>;
  items?: SchemaProperty;
  required?: string[];
  [key: string]: any;
}

export interface FieldMetadata {
  name: string;
  type: string;
  label: string;
  description?: string;
  required: boolean;
  defaultValue?: any;
  validation?: {
    minLength?: number;
    maxLength?: number;
    min?: number;
    max?: number;
    pattern?: string;
  };
  options?: Array<{ value: any; label: string }>;
  isArray?: boolean;
  isNullable?: boolean;
}

/**
 * Extract field metadata from JSON Schema for form generation
 */
export function extractFieldMetadata(
  fieldName: string,
  fieldSchema: SchemaProperty,
  isRequired: boolean = false
): FieldMetadata {
  // Handle anyOf (union types)
  let actualSchema = fieldSchema;
  let isNullable = false;

  if (fieldSchema.anyOf) {
    // Find non-null type
    const nonNullTypes = fieldSchema.anyOf.filter((s: any) => s.type !== 'null');
    if (nonNullTypes.length > 0) {
      actualSchema = nonNullTypes[0];
    }
    isNullable = fieldSchema.anyOf.some((s: any) => s.type === 'null');
  }

  // Determine field type
  let fieldType = 'text';
  const schemaType = actualSchema.type;

  if (schemaType === 'string') {
    fieldType = actualSchema.format === 'email' ? 'email' :
                actualSchema.format === 'date' ? 'date' :
                actualSchema.format === 'date-time' ? 'datetime-local' :
                actualSchema.format === 'uri' ? 'url' :
                actualSchema.maxLength && actualSchema.maxLength > 100 ? 'textarea' :
                'text';
  } else if (schemaType === 'number' || schemaType === 'integer') {
    fieldType = 'number';
  } else if (schemaType === 'boolean') {
    fieldType = 'checkbox';
  } else if (schemaType === 'array') {
    fieldType = 'array';
  } else if (schemaType === 'object') {
    fieldType = 'object';
  }

  // Handle enums (select dropdowns)
  if (actualSchema.enum) {
    fieldType = 'select';
  }

  // Extract validation rules
  const validation: FieldMetadata['validation'] = {};
  if (actualSchema.minLength !== undefined) {
    validation.minLength = actualSchema.minLength;
  }
  if (actualSchema.maxLength !== undefined) {
    validation.maxLength = actualSchema.maxLength;
  }
  if (actualSchema.minimum !== undefined) {
    validation.min = actualSchema.minimum;
  }
  if (actualSchema.maximum !== undefined) {
    validation.max = actualSchema.maximum;
  }
  if (actualSchema.pattern) {
    validation.pattern = actualSchema.pattern;
  }

  // Extract enum options
  let options: FieldMetadata['options'];
  if (actualSchema.enum) {
    options = actualSchema.enum.map((value: any) => ({
      value,
      label: String(value)
    }));
  }

  return {
    name: fieldName,
    type: fieldType,
    label: actualSchema.title || formatFieldName(fieldName),
    description: actualSchema.description,
    required: isRequired && !isNullable,
    defaultValue: fieldSchema.default,
    validation: Object.keys(validation).length > 0 ? validation : undefined,
    options,
    isArray: schemaType === 'array',
    isNullable,
  };
}

/**
 * Generate field metadata for all fields in a schema
 */
export function generateFormFields(
  validatorClass: { getSchema(): any }
): FieldMetadata[] {
  const schema = validatorClass.getSchema();
  const properties = schema.properties || {};
  const requiredFields = new Set(schema.required || []);

  return Object.entries(properties).map(([fieldName, fieldSchema]) =>
    extractFieldMetadata(fieldName, fieldSchema as SchemaProperty, requiredFields.has(fieldName))
  );
}

/**
 * Convert camelCase or snake_case to Title Case
 */
function formatFieldName(name: string): string {
  return name
    .replace(/([A-Z])/g, ' $1')
    .replace(/_/g, ' ')
    .replace(/^./, (str) => str.toUpperCase())
    .trim();
}

/**
 * Generate HTML5 validation attributes from schema
 */
export function getHtmlValidationAttributes(field: FieldMetadata): Record<string, any> {
  const attrs: Record<string, any> = {};

  if (field.required) {
    attrs.required = true;
  }

  if (field.validation) {
    if (field.validation.minLength !== undefined) {
      attrs.minLength = field.validation.minLength;
    }
    if (field.validation.maxLength !== undefined) {
      attrs.maxLength = field.validation.maxLength;
    }
    if (field.validation.min !== undefined) {
      attrs.min = field.validation.min;
    }
    if (field.validation.max !== undefined) {
      attrs.max = field.validation.max;
    }
    if (field.validation.pattern) {
      attrs.pattern = field.validation.pattern;
    }
  }

  return attrs;
}

/**
 * Generate default form values from schema
 */
export function generateDefaultValues(
  validatorClass: { getSchema(): any }
): Record<string, any> {
  const schema = validatorClass.getSchema();
  const properties = schema.properties || {};
  const defaults: Record<string, any> = {};

  Object.entries(properties).forEach(([fieldName, fieldSchema]: [string, any]) => {
    if (fieldSchema.default !== undefined) {
      defaults[fieldName] = fieldSchema.default;
    }
  });

  return defaults;
}

/**
 * Generate validation rules for React Hook Form
 */
export function generateReactHookFormRules(field: FieldMetadata) {
  const rules: any = {};

  if (field.required) {
    rules.required = `${field.label} is required`;
  }

  if (field.validation) {
    if (field.validation.minLength !== undefined) {
      rules.minLength = {
        value: field.validation.minLength,
        message: `${field.label} must be at least ${field.validation.minLength} characters`
      };
    }

    if (field.validation.maxLength !== undefined) {
      rules.maxLength = {
        value: field.validation.maxLength,
        message: `${field.label} must not exceed ${field.validation.maxLength} characters`
      };
    }

    if (field.validation.min !== undefined) {
      rules.min = {
        value: field.validation.min,
        message: `${field.label} must be at least ${field.validation.min}`
      };
    }

    if (field.validation.max !== undefined) {
      rules.max = {
        value: field.validation.max,
        message: `${field.label} must not exceed ${field.validation.max}`
      };
    }

    if (field.validation.pattern) {
      rules.pattern = {
        value: new RegExp(field.validation.pattern),
        message: `${field.label} has invalid format`
      };
    }
  }

  // Type-specific validation
  if (field.type === 'email') {
    rules.pattern = {
      value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
      message: 'Invalid email address'
    };
  }

  if (field.type === 'url') {
    rules.pattern = {
      value: /^https?:\/\/.+/i,
      message: 'Invalid URL'
    };
  }

  return rules;
}

/**
 * Generate Yup validation schema from JSON Schema
 * Note: Requires yup to be installed
 */
export function generateYupSchema(validatorClass: { getSchema(): any }): string {
  const fields = generateFormFields(validatorClass);

  const yupFields = fields.map(field => {
    let yupField = '';

    // Base type
    switch (field.type) {
      case 'text':
      case 'email':
      case 'url':
      case 'textarea':
        yupField = 'yup.string()';
        break;
      case 'number':
        yupField = 'yup.number()';
        break;
      case 'checkbox':
        yupField = 'yup.boolean()';
        break;
      case 'date':
      case 'datetime-local':
        yupField = 'yup.date()';
        break;
      case 'array':
        yupField = 'yup.array()';
        break;
      case 'object':
        yupField = 'yup.object()';
        break;
      default:
        yupField = 'yup.mixed()';
    }

    // Add validations
    if (field.required) {
      yupField += `.required('${field.label} is required')`;
    }

    if (field.validation) {
      if (field.validation.minLength !== undefined) {
        yupField += `.min(${field.validation.minLength}, '${field.label} must be at least ${field.validation.minLength} characters')`;
      }
      if (field.validation.maxLength !== undefined) {
        yupField += `.max(${field.validation.maxLength}, '${field.label} must not exceed ${field.validation.maxLength} characters')`;
      }
      if (field.validation.min !== undefined) {
        yupField += `.min(${field.validation.min})`;
      }
      if (field.validation.max !== undefined) {
        yupField += `.max(${field.validation.max})`;
      }
    }

    if (field.type === 'email') {
      yupField += `.email('Invalid email address')`;
    }

    if (field.type === 'url') {
      yupField += `.url('Invalid URL')`;
    }

    return `  ${field.name}: ${yupField}`;
  });

  return `yup.object({\n${yupFields.join(',\n')}\n})`;
}

/**
 * Format schema for display (useful for debugging/documentation)
 */
export function formatSchemaForDisplay(validatorClass: { getSchema(): any }): string {
  const schema = validatorClass.getSchema();
  const fields = generateFormFields(validatorClass);

  return fields.map(field => {
    const parts = [
      `**${field.label}** (${field.name})`,
      `  Type: ${field.type}`,
      field.required ? '  Required: Yes' : '  Required: No',
      field.description ? `  Description: ${field.description}` : null,
      field.defaultValue !== undefined ? `  Default: ${JSON.stringify(field.defaultValue)}` : null,
      field.options ? `  Options: ${field.options.map(o => o.value).join(', ')}` : null,
    ].filter(Boolean);

    return parts.join('\n');
  }).join('\n\n');
}