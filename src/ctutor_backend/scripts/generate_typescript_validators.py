#!/usr/bin/env python3
"""
Generate TypeScript validation classes from JSON schemas exported from Pydantic models.

This script creates runtime validation classes that:
1. Accept JSON data from API responses
2. Validate against the schema
3. Return typed instances with proper error handling
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class ValidationClassGenerator:
    """Generate TypeScript validation classes from JSON schemas."""

    def __init__(self, include_timestamp: bool = False):
        self.include_timestamp = include_timestamp
        self._timestamp_value: Optional[str] = None
        self.type_imports: Set[str] = set()

    def _current_timestamp(self) -> str:
        """Get current timestamp for this generation run."""
        if not self.include_timestamp:
            raise RuntimeError("Timestamp requested but include_timestamp is False")
        if self._timestamp_value is None:
            self._timestamp_value = datetime.now().isoformat()
        return self._timestamp_value

    def generate_from_schemas(self, schema_dir: Path, output_dir: Path) -> List[Path]:
        """Generate validation classes from schema files."""
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.include_timestamp:
            self._timestamp_value = None

        generated_files = []

        # Find all schema files
        schema_files = list(schema_dir.glob("*.schema.json"))

        if not schema_files:
            print(f"⚠️  No schema files found in {schema_dir}")
            return generated_files

        print(f"📦 Found {len(schema_files)} schema files")

        # Generate validation classes for each category
        for schema_file in schema_files:
            if schema_file.stem == "index":
                continue

            category = schema_file.stem.replace('.schema', '')
            output_file = self._generate_category_validators(schema_file, output_dir, category)
            if output_file:
                generated_files.append(output_file)

        # Generate index file
        if generated_files:
            index_file = self._generate_index(generated_files, output_dir)
            generated_files.append(index_file)

        # Generate base validator class
        base_file = self._generate_base_validator(output_dir)
        generated_files.insert(0, base_file)

        return generated_files

    def _generate_category_validators(self, schema_file: Path, output_dir: Path, category: str) -> Optional[Path]:
        """Generate validators for a single category."""
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_bundle = json.load(f)
        except Exception as e:
            print(f"❌ Error reading schema file {schema_file}: {e}")
            return None

        models = schema_bundle.get('models', {})
        enums = schema_bundle.get('enums', {})

        if not models and not enums:
            return None

        self.type_imports.clear()

        # Generate content
        lines = []

        # Header
        lines.append("/**")
        lines.append(f" * Auto-generated validation classes for {category.title()} models")
        if self.include_timestamp:
            lines.append(f" * Generated on: {self._current_timestamp()}")
        lines.append(" * DO NOT EDIT MANUALLY")
        lines.append(" */")
        lines.append("")

        # Imports
        lines.append(f"import type {{ {', '.join(sorted(models.keys()))} }} from '../generated/{category}';")

        # Import enums if any
        if enums:
            lines.append(f"import {{ {', '.join(sorted(enums.keys()))} }} from '../generated/{category}';")

        lines.append("import { BaseValidator, ValidationError } from './BaseValidator';")
        lines.append("")

        # Generate enum validators (if any)
        for enum_name, enum_schema in enums.items():
            enum_validator = self._generate_enum_validator(enum_name, enum_schema)
            lines.extend(enum_validator)
            lines.append("")

        # Generate model validators
        for model_name, model_schema in models.items():
            validator_class = self._generate_validator_class(model_name, model_schema, category)
            lines.extend(validator_class)
            lines.append("")

        # Write file
        output_file = output_dir / f"{category}.validators.ts"
        content = '\n'.join(lines)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ Generated validators: {output_file}")
        return output_file

    def _generate_enum_validator(self, enum_name: str, enum_schema: Dict[str, Any]) -> List[str]:
        """Generate validator function for an enum."""
        lines = []

        enum_values = enum_schema.get('enum', [])
        values_str = ', '.join([f"'{v}'" if isinstance(v, str) else str(v) for v in enum_values])

        lines.append(f"export function validate{enum_name}(value: any): {enum_name} {{")
        lines.append(f"  const validValues = [{values_str}];")
        lines.append("  if (!validValues.includes(value)) {")
        lines.append(f"    throw new ValidationError('{enum_name}', `Invalid value: ${{value}}. Expected one of: ${{validValues.join(', ')}}`);")
        lines.append("  }")
        lines.append(f"  return value as {enum_name};")
        lines.append("}")

        return lines

    def _generate_validator_class(self, model_name: str, model_schema: Dict[str, Any], category: str) -> List[str]:
        """Generate a validation class for a model."""
        lines = []

        # Class JSDoc
        description = model_schema.get('description', f'Validator for {model_name}')
        lines.append("/**")
        lines.append(f" * {description}")
        lines.append(" */")

        # Class definition
        class_name = f"{model_name}Validator"
        lines.append(f"export class {class_name} extends BaseValidator<{model_name}> {{")

        # Static schema property
        lines.append("  /**")
        lines.append("   * JSON Schema for this model")
        lines.append("   * Useful for form generation, validation, and documentation")
        lines.append("   */")

        # Serialize schema to JSON string (escape special characters)
        schema_json = json.dumps(model_schema, indent=2)
        # Escape backticks and ${} for template literals
        schema_json = schema_json.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')

        lines.append(f"  static readonly schema = JSON.parse(`{schema_json}`) as const;")
        lines.append("")

        # Static helper methods
        lines.append("  /**")
        lines.append("   * Get schema for a specific field")
        lines.append("   */")
        lines.append("  static getFieldSchema(fieldName: string): any {")
        lines.append("    return this.schema.properties?.[fieldName];")
        lines.append("  }")
        lines.append("")

        lines.append("  /**")
        lines.append("   * Check if a field is required")
        lines.append("   */")
        lines.append("  static isFieldRequired(fieldName: string): boolean {")
        lines.append("    return this.schema.required?.includes(fieldName) ?? false;")
        lines.append("  }")
        lines.append("")

        lines.append("  /**")
        lines.append("   * Get all required field names")
        lines.append("   */")
        lines.append("  static getRequiredFields(): string[] {")
        lines.append("    return this.schema.required ?? [];")
        lines.append("  }")
        lines.append("")

        lines.append("  /**")
        lines.append("   * Get all field names")
        lines.append("   */")
        lines.append("  static getFields(): string[] {")
        lines.append("    return Object.keys(this.schema.properties ?? {});")
        lines.append("  }")
        lines.append("")

        # Validate method
        lines.append(f"  validate(data: any): {model_name} {{")
        lines.append("    const errors: string[] = [];")
        lines.append("")

        # Check if data is object
        lines.append("    if (typeof data !== 'object' || data === null) {")
        lines.append(f"      throw new ValidationError('{model_name}', 'Expected an object');")
        lines.append("    }")
        lines.append("")

        # Get properties and required fields
        properties = model_schema.get('properties', {})
        required_fields = set(model_schema.get('required', []))

        # Validate each field
        for field_name, field_schema in properties.items():
            field_validation = self._generate_field_validation(
                field_name,
                field_schema,
                field_name in required_fields,
                model_name
            )
            lines.extend(field_validation)
            lines.append("")

        # Return errors or validated object
        lines.append("    if (errors.length > 0) {")
        lines.append(f"      throw new ValidationError('{model_name}', errors.join('; '));")
        lines.append("    }")
        lines.append("")
        lines.append(f"    return data as {model_name};")
        lines.append("  }")

        # Safe validate method
        lines.append("")
        lines.append(f"  safeValidate(data: any): {{ success: true; data: {model_name} }} | {{ success: false; error: ValidationError }} {{")
        lines.append("    try {")
        lines.append("      const validData = this.validate(data);")
        lines.append("      return { success: true, data: validData };")
        lines.append("    } catch (error) {")
        lines.append("      if (error instanceof ValidationError) {")
        lines.append("        return { success: false, error };")
        lines.append("      }")
        lines.append(f"      return {{ success: false, error: new ValidationError('{model_name}', String(error)) }};")
        lines.append("    }")
        lines.append("  }")

        lines.append("}")

        return lines

    def _generate_field_validation(
        self,
        field_name: str,
        field_schema: Dict[str, Any],
        is_required: bool,
        model_name: str
    ) -> List[str]:
        """Generate validation code for a single field."""
        lines = []

        # Handle required vs optional
        if is_required:
            lines.append(f"    // Required field: {field_name}")
            lines.append(f"    if (!('{field_name}' in data)) {{")
            lines.append(f"      errors.push('Missing required field: {field_name}');")
            lines.append("    } else {")
            indent = "      "
        else:
            lines.append(f"    // Optional field: {field_name}")
            lines.append(f"    if ('{field_name}' in data && data.{field_name} !== undefined && data.{field_name} !== null) {{")
            indent = "      "

        # Get field type and validation
        field_type = field_schema.get('type')
        field_ref = field_schema.get('$ref')

        if field_ref:
            # Reference to another model - skip deep validation for now
            lines.append(f"{indent}// Reference field - basic object check")
            lines.append(f"{indent}if (typeof data.{field_name} !== 'object') {{")
            lines.append(f"{indent}  errors.push('Field {field_name} must be an object');")
            lines.append(f"{indent}}}")
        elif 'anyOf' in field_schema or 'oneOf' in field_schema:
            # Union types - basic validation
            lines.append(f"{indent}// Union type - skipping detailed validation")
        elif field_type == 'array':
            lines.append(f"{indent}if (!Array.isArray(data.{field_name})) {{")
            lines.append(f"{indent}  errors.push('Field {field_name} must be an array');")
            lines.append(f"{indent}}}")
            # TODO: Validate array items
        elif field_type == 'string':
            lines.append(f"{indent}if (typeof data.{field_name} !== 'string') {{")
            lines.append(f"{indent}  errors.push('Field {field_name} must be a string');")
            lines.append(f"{indent}}}")
        elif field_type == 'number' or field_type == 'integer':
            lines.append(f"{indent}if (typeof data.{field_name} !== 'number') {{")
            lines.append(f"{indent}  errors.push('Field {field_name} must be a number');")
            lines.append(f"{indent}}}")
        elif field_type == 'boolean':
            lines.append(f"{indent}if (typeof data.{field_name} !== 'boolean') {{")
            lines.append(f"{indent}  errors.push('Field {field_name} must be a boolean');")
            lines.append(f"{indent}}}")
        elif field_type == 'object':
            lines.append(f"{indent}if (typeof data.{field_name} !== 'object' || data.{field_name} === null) {{")
            lines.append(f"{indent}  errors.push('Field {field_name} must be an object');")
            lines.append(f"{indent}}}")
        else:
            # Unknown type - skip validation
            lines.append(f"{indent}// Type validation for {field_name} skipped")

        lines.append("    }")

        return lines

    def _generate_base_validator(self, output_dir: Path) -> Path:
        """Generate the base validator class."""
        lines = []

        lines.append("/**")
        lines.append(" * Base validator class with error handling")
        if self.include_timestamp:
            lines.append(f" * Generated on: {self._current_timestamp()}")
        lines.append(" * DO NOT EDIT MANUALLY")
        lines.append(" */")
        lines.append("")

        lines.append("export class ValidationError extends Error {")
        lines.append("  constructor(")
        lines.append("    public readonly modelName: string,")
        lines.append("    public readonly validationMessage: string")
        lines.append("  ) {")
        lines.append("    super(`Validation failed for ${modelName}: ${validationMessage}`);")
        lines.append("    this.name = 'ValidationError';")
        lines.append("  }")
        lines.append("}")
        lines.append("")

        lines.append("export abstract class BaseValidator<T> {")
        lines.append("  /**")
        lines.append("   * Validate data and return typed instance")
        lines.append("   * @throws ValidationError if validation fails")
        lines.append("   */")
        lines.append("  abstract validate(data: any): T;")
        lines.append("")
        lines.append("  /**")
        lines.append("   * Safe validation that returns result object instead of throwing")
        lines.append("   */")
        lines.append("  abstract safeValidate(data: any): { success: true; data: T } | { success: false; error: ValidationError };")
        lines.append("")
        lines.append("  /**")
        lines.append("   * Validate array of items")
        lines.append("   */")
        lines.append("  validateArray(data: any[]): T[] {")
        lines.append("    return data.map((item, index) => {")
        lines.append("      try {")
        lines.append("        return this.validate(item);")
        lines.append("      } catch (error) {")
        lines.append("        if (error instanceof ValidationError) {")
        lines.append("          throw new ValidationError(")
        lines.append("            error.modelName,")
        lines.append("            `Item at index ${index}: ${error.validationMessage}`")
        lines.append("          );")
        lines.append("        }")
        lines.append("        throw error;")
        lines.append("      }")
        lines.append("    });")
        lines.append("  }")
        lines.append("}")

        output_file = output_dir / "BaseValidator.ts"
        content = '\n'.join(lines) + '\n'

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ Generated base validator: {output_file}")
        return output_file

    def _generate_index(self, generated_files: List[Path], output_dir: Path) -> Path:
        """Generate index file that exports all validators."""
        lines = []

        lines.append("/**")
        lines.append(" * Auto-generated validator exports")
        if self.include_timestamp:
            lines.append(f" * Generated on: {self._current_timestamp()}")
        lines.append(" */")
        lines.append("")

        lines.append("export * from './BaseValidator';")
        lines.append("")

        # Export from each category file
        for file_path in sorted(generated_files):
            if file_path.name != "BaseValidator.ts" and file_path.name != "index.ts":
                module_name = file_path.stem
                lines.append(f"export * from './{module_name}';")

        output_file = output_dir / "index.ts"
        content = '\n'.join(lines) + '\n'

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ Generated validator index: {output_file}")
        return output_file


def main(
    schema_dir: Path | None = None,
    output_dir: Path | None = None,
    include_timestamp: bool = False
) -> List[Path]:
    """Main entry point."""
    backend_dir = Path(__file__).parent.parent
    src_dir = backend_dir.parent
    project_root = src_dir.parent

    if schema_dir is None:
        schema_dir = project_root / "frontend" / "src" / "types" / "schemas"

    if output_dir is None:
        output_dir = project_root / "frontend" / "src" / "types" / "validators"

    print("🚀 TypeScript Validator Generator")
    print("=" * 50)
    print(f"📂 Schema directory: {schema_dir}")
    print(f"📁 Output directory: {output_dir}")
    print("=" * 50)

    generator = ValidationClassGenerator(include_timestamp=include_timestamp)
    generated_files = generator.generate_from_schemas(schema_dir, output_dir)

    print("=" * 50)
    print(f"✅ Generated {len(generated_files)} validator files")
    return generated_files


if __name__ == "__main__":
    main()
