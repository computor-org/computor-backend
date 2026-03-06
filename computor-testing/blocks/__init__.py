"""
Computor Framework - Test Case Blocks

Pydantic models defining available test types, qualifications, and options
for each supported programming language. These models can be exported to
JSON Schema and TypeScript interfaces for use in VSCode extensions.
"""

from .models import (
    # Core types
    FieldType,
    FieldDefinition,
    QualificationBlock,
    TestTypeBlock,
    LanguageBlocks,
    BlockRegistry,
    # Template types
    TestTemplate,
    TemplateCategory,
    # Utility functions
    get_language_blocks,
    get_all_blocks,
    export_json_schema,
    export_test_yaml_schema,
    export_typescript,
    export_field_visibility,
    get_field_visibility_map,
    # Template functions
    generate_test_yaml,
    generate_full_test_yaml,
    get_templates,
    get_templates_by_test_type,
    export_templates_json,
)

__version__ = "0.1.0"
