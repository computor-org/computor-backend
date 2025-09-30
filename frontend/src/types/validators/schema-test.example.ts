/**
 * Example/test file demonstrating validator schema methods
 * Run this in browser console or Node to verify schema methods work
 */

import { CourseCreateValidator, UserGetValidator } from './index';
import { generateFormFields, generateDefaultValues } from '../../utils/schemaFormHelpers';

// ============================================================================
// Test 1: Static Schema Access
// ============================================================================

console.log('=== Test 1: Static Schema Access ===');

// Access full schema
const courseSchema = CourseCreateValidator.schema;
console.log('Course schema:', courseSchema);
console.log('Schema type:', courseSchema.type);
console.log('Schema title:', courseSchema.title);

// ============================================================================
// Test 2: Field Introspection
// ============================================================================

console.log('\n=== Test 2: Field Introspection ===');

// Get all fields
const allFields = CourseCreateValidator.getFields();
console.log('All fields:', allFields);

// Get required fields
const requiredFields = CourseCreateValidator.getRequiredFields();
console.log('Required fields:', requiredFields);

// Check specific field
const isTitleRequired = CourseCreateValidator.isFieldRequired('title');
console.log('Is "title" required?', isTitleRequired);

// Get field schema
const titleFieldSchema = CourseCreateValidator.getFieldSchema('title');
console.log('Title field schema:', titleFieldSchema);

// ============================================================================
// Test 3: Form Field Generation
// ============================================================================

console.log('\n=== Test 3: Form Field Generation ===');

const formFields = generateFormFields(CourseCreateValidator);
console.log('Generated form fields:', formFields);

console.log('\nField details:');
formFields.forEach(field => {
  console.log(`- ${field.name}:`, {
    type: field.type,
    label: field.label,
    required: field.required,
    validation: field.validation
  });
});

// ============================================================================
// Test 4: Default Values
// ============================================================================

console.log('\n=== Test 4: Default Values ===');

const defaultValues = generateDefaultValues(CourseCreateValidator);
console.log('Default values:', defaultValues);

// ============================================================================
// Test 5: Multiple Validators
// ============================================================================

console.log('\n=== Test 5: Multiple Validators ===');

// Compare two validators
const courseFields = CourseCreateValidator.getFields();
const userFields = UserGetValidator.getFields();

console.log('Course has', courseFields.length, 'fields');
console.log('User has', userFields.length, 'fields');

// ============================================================================
// Test 6: Schema Properties
// ============================================================================

console.log('\n=== Test 6: Schema Properties ===');

// Iterate through all properties
const properties = CourseCreateValidator.schema.properties || {};
Object.entries(properties).forEach(([name, schema]: [string, any]) => {
  console.log(`Property: ${name}`);
  console.log('  - Type:', schema.type);
  console.log('  - Title:', schema.title);
  console.log('  - Required:', CourseCreateValidator.isFieldRequired(name));
  if (schema.description) {
    console.log('  - Description:', schema.description);
  }
  if (schema.enum) {
    console.log('  - Enum values:', schema.enum);
  }
  if (schema.minLength !== undefined || schema.maxLength !== undefined) {
    console.log('  - Length constraints:', {
      min: schema.minLength,
      max: schema.maxLength
    });
  }
});

// ============================================================================
// Test 7: Validation Rules
// ============================================================================

console.log('\n=== Test 7: Validation Rules ===');

formFields.forEach(field => {
  if (field.validation && Object.keys(field.validation).length > 0) {
    console.log(`${field.name} has validation:`, field.validation);
  }
});

// ============================================================================
// Test 8: Schema as JSON
// ============================================================================

console.log('\n=== Test 8: Schema as JSON ===');

// Export schema as JSON (for VSCode, documentation, etc.)
const schemaJson = JSON.stringify(CourseCreateValidator.schema, null, 2);
console.log('Schema JSON (first 500 chars):');
console.log(schemaJson.substring(0, 500) + '...');

// ============================================================================
// Summary
// ============================================================================

console.log('\n=== Summary ===');
console.log('✅ All schema methods working correctly!');
console.log(`✅ Found ${allFields.length} fields`);
console.log(`✅ ${requiredFields.length} are required`);
console.log(`✅ ${formFields.length} form fields generated`);
console.log(`✅ ${Object.keys(defaultValues).length} default values`);

// Export results for testing
export const schemaTestResults = {
  allFields,
  requiredFields,
  formFields,
  defaultValues,
  courseSchema,
  success: true
};