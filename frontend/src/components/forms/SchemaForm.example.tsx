/**
 * Example: Dynamic form generation from validator schemas
 *
 * This demonstrates how to use validator classes with static schema
 * to automatically generate forms with validation.
 */

import React from 'react';
import { useForm, FieldError } from 'react-hook-form';
import {
  generateFormFields,
  generateDefaultValues,
  generateReactHookFormRules,
  getHtmlValidationAttributes,
  type FieldMetadata
} from '../../utils/schemaFormHelpers';

// Example validators (import your actual validators)
import { CourseCreateValidator, UserCreateValidator } from '../../types/validators';

// ============================================================================
// Example 1: Basic Schema-Driven Form
// ============================================================================

interface SchemaFormProps<T> {
  validatorClass: { schema: any };
  onSubmit: (data: T) => void | Promise<void>;
  submitLabel?: string;
}

/**
 * Generic form component that generates fields from validator schema
 */
export function SchemaForm<T>({
  validatorClass,
  onSubmit,
  submitLabel = 'Submit'
}: SchemaFormProps<T>) {
  const fields = generateFormFields(validatorClass);
  const defaultValues = generateDefaultValues(validatorClass);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<any>({
    defaultValues
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {fields.map(field => (
        <FormField
          key={field.name}
          field={field}
          register={register}
          error={errors[field.name] as FieldError}
        />
      ))}

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Submitting...' : submitLabel}
      </button>
    </form>
  );
}

/**
 * Render a single form field based on schema metadata
 */
function FormField({
  field,
  register,
  error
}: {
  field: FieldMetadata;
  register: any;
  error?: FieldError;
}) {
  const rules = generateReactHookFormRules(field);
  const htmlAttrs = getHtmlValidationAttributes(field);

  return (
    <div className="form-field">
      <label htmlFor={field.name}>
        {field.label}
        {field.required && <span className="required">*</span>}
      </label>

      {field.description && (
        <p className="field-description">{field.description}</p>
      )}

      {field.type === 'textarea' ? (
        <textarea
          id={field.name}
          {...register(field.name, rules)}
          {...htmlAttrs}
        />
      ) : field.type === 'select' && field.options ? (
        <select
          id={field.name}
          {...register(field.name, rules)}
          {...htmlAttrs}
        >
          <option value="">-- Select {field.label} --</option>
          {field.options.map(opt => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      ) : field.type === 'checkbox' ? (
        <input
          type="checkbox"
          id={field.name}
          {...register(field.name, rules)}
        />
      ) : (
        <input
          type={field.type}
          id={field.name}
          {...register(field.name, rules)}
          {...htmlAttrs}
        />
      )}

      {error && <span className="error">{error.message}</span>}
    </div>
  );
}

// Usage:
export function CreateCourseForm() {
  const handleSubmit = async (data: any) => {
    // Validate with runtime validator before submitting
    const validator = new CourseCreateValidator();
    const validated = validator.validate(data);

    // Submit to API
    console.log('Validated data:', validated);
  };

  return (
    <SchemaForm
      validatorClass={CourseCreateValidator}
      onSubmit={handleSubmit}
      submitLabel="Create Course"
    />
  );
}

// ============================================================================
// Example 2: Material-UI Form with Schema
// ============================================================================

import { TextField, Button, Checkbox, FormControlLabel, Select, MenuItem } from '@mui/material';

export function MaterialSchemaForm<T>({
  validatorClass,
  onSubmit,
  submitLabel = 'Submit'
}: SchemaFormProps<T>) {
  const fields = generateFormFields(validatorClass);
  const defaultValues = generateDefaultValues(validatorClass);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<any>({
    defaultValues
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {fields.map(field => {
        const rules = generateReactHookFormRules(field);
        const error = errors[field.name] as FieldError;

        if (field.type === 'checkbox') {
          return (
            <FormControlLabel
              key={field.name}
              control={<Checkbox {...register(field.name, rules)} />}
              label={field.label}
            />
          );
        }

        if (field.type === 'select' && field.options) {
          return (
            <TextField
              key={field.name}
              select
              label={field.label}
              required={field.required}
              error={!!error}
              helperText={error?.message || field.description}
              {...register(field.name, rules)}
            >
              {field.options.map(opt => (
                <MenuItem key={opt.value} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </TextField>
          );
        }

        return (
          <TextField
            key={field.name}
            label={field.label}
            type={field.type === 'textarea' ? 'text' : field.type}
            multiline={field.type === 'textarea'}
            rows={field.type === 'textarea' ? 4 : 1}
            required={field.required}
            error={!!error}
            helperText={error?.message || field.description}
            {...register(field.name, rules)}
          />
        );
      })}

      <Button type="submit" variant="contained" disabled={isSubmitting}>
        {isSubmitting ? 'Submitting...' : submitLabel}
      </Button>
    </form>
  );
}

// ============================================================================
// Example 3: Using Schema for Field Introspection
// ============================================================================

/**
 * Get schema information programmatically
 */
export function SchemaIntrospectionExample() {
  // Access static schema methods
  const fields = CourseCreateValidator.getFields();
  const requiredFields = CourseCreateValidator.getRequiredFields();

  console.log('All fields:', fields);
  // => ['title', 'description', 'start_date', ...]

  console.log('Required fields:', requiredFields);
  // => ['title', 'start_date']

  // Check if specific field is required
  const isTitleRequired = CourseCreateValidator.isFieldRequired('title');
  console.log('Is title required?', isTitleRequired); // => true

  // Get schema for specific field
  const titleSchema = CourseCreateValidator.getFieldSchema('title');
  console.log('Title field schema:', titleSchema);
  // => { type: 'string', title: 'Title', maxLength: 255, ... }

  // Access full schema
  const fullSchema = CourseCreateValidator.schema;
  console.log('Full schema:', fullSchema);

  return null;
}

// ============================================================================
// Example 4: Conditional Field Rendering
// ============================================================================

export function ConditionalSchemaForm() {
  const fields = generateFormFields(CourseCreateValidator);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors }
  } = useForm();

  // Watch a field value
  const courseType = watch('course_type');

  return (
    <form onSubmit={handleSubmit(data => console.log(data))}>
      {fields.map(field => {
        // Skip fields based on conditions
        if (field.name === 'advanced_options' && courseType !== 'advanced') {
          return null;
        }

        return (
          <FormField
            key={field.name}
            field={field}
            register={register}
            error={errors[field.name] as FieldError}
          />
        );
      })}

      <button type="submit">Submit</button>
    </form>
  );
}

// ============================================================================
// Example 5: Schema Documentation Component
// ============================================================================

import { formatSchemaForDisplay } from '../../utils/schemaFormHelpers';

/**
 * Display schema documentation for developers/users
 */
export function SchemaDocumentation({ validatorClass }: { validatorClass: any }) {
  const fields = generateFormFields(validatorClass);
  const markdown = formatSchemaForDisplay(validatorClass);

  return (
    <div className="schema-docs">
      <h2>Schema: {validatorClass.schema.title}</h2>
      {validatorClass.schema.description && (
        <p>{validatorClass.schema.description}</p>
      )}

      <h3>Fields</h3>
      <table>
        <thead>
          <tr>
            <th>Field</th>
            <th>Type</th>
            <th>Required</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {fields.map(field => (
            <tr key={field.name}>
              <td><code>{field.name}</code></td>
              <td>{field.type}</td>
              <td>{field.required ? '✅' : '❌'}</td>
              <td>{field.description || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>JSON Schema</h3>
      <pre>{JSON.stringify(validatorClass.schema, null, 2)}</pre>
    </div>
  );
}

// ============================================================================
// Example 6: VSCode Extension Helper
// ============================================================================

/**
 * Generate JSON Schema file for VSCode validation
 * This can be used in VSCode settings.json to validate JSON files
 */
export function exportSchemaForVSCode(validatorClass: any, fileName: string) {
  const schema = {
    $schema: 'http://json-schema.org/draft-07/schema#',
    ...validatorClass.schema
  };

  const blob = new Blob([JSON.stringify(schema, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${fileName}.schema.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// Usage:
export function ExportSchemaButton() {
  return (
    <button onClick={() => exportSchemaForVSCode(CourseCreateValidator, 'course-create')}>
      Export Course Schema for VSCode
    </button>
  );
}

// ============================================================================
// Example 7: Dynamic Form Wizard
// ============================================================================

/**
 * Multi-step form wizard based on schema fields
 */
export function SchemaFormWizard({ validatorClass, onSubmit }: SchemaFormProps<any>) {
  const fields = generateFormFields(validatorClass);
  const [currentStep, setCurrentStep] = React.useState(0);

  // Split fields into steps (e.g., 3 fields per step)
  const fieldsPerStep = 3;
  const steps = [];
  for (let i = 0; i < fields.length; i += fieldsPerStep) {
    steps.push(fields.slice(i, i + fieldsPerStep));
  }

  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm();

  const currentFields = steps[currentStep] || [];
  const isLastStep = currentStep === steps.length - 1;

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <h3>Step {currentStep + 1} of {steps.length}</h3>

      {currentFields.map(field => (
        <FormField
          key={field.name}
          field={field}
          register={register}
          error={errors[field.name] as FieldError}
        />
      ))}

      <div className="wizard-buttons">
        {currentStep > 0 && (
          <button type="button" onClick={() => setCurrentStep(currentStep - 1)}>
            Previous
          </button>
        )}

        {isLastStep ? (
          <button type="submit">Submit</button>
        ) : (
          <button type="button" onClick={() => setCurrentStep(currentStep + 1)}>
            Next
          </button>
        )}
      </div>
    </form>
  );
}

// ============================================================================
// Example 8: Schema Comparison
// ============================================================================

/**
 * Compare two schemas (useful for version migrations)
 */
export function compareSchemas(validatorA: any, validatorB: any) {
  const fieldsA = new Set(validatorA.getFields());
  const fieldsB = new Set(validatorB.getFields());

  const added = [...fieldsB].filter(f => !fieldsA.has(f));
  const removed = [...fieldsA].filter(f => !fieldsB.has(f));
  const common = [...fieldsA].filter(f => fieldsB.has(f));

  return {
    added,
    removed,
    common,
    hasChanges: added.length > 0 || removed.length > 0
  };
}

// Usage:
const diff = compareSchemas(CourseCreateValidator, UserCreateValidator);
console.log('Schema differences:', diff);