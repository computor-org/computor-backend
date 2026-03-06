# Computor Framework - Blocks

A Pydantic-based module that defines test case blocks (types, qualifications, fields) for each supported programming language. Designed to export to JSON Schema and TypeScript for use in VSCode extensions, and to generate `test.yaml` files.

## Installation

The `blocks` CLI is included with the Computor Framework:

```bash
cd computor-testing
pip install -e .

# Verify installation
blocks --version
```

---

## Quick Start

### List Available Blocks

```bash
# List all languages
blocks list

# List specific language
blocks list -l python
blocks list -l c
```

### Generate test.yaml

```bash
# Initialize a new test.yaml
blocks init -l python -n "My Tests"

# Generate a test snippet
blocks generate -l python -t variable -n result

# Use pre-built templates
blocks templates list
blocks templates show "Variable Check" -l python
```

### Export for VSCode Extension

```bash
# Export all formats to a directory
blocks export ./generated

# Individual exports
blocks schema -o blocks.schema.json      # JSON Schema
blocks typescript -o blocks.types.ts     # TypeScript interfaces
blocks data -o blocks.data.json          # Raw block data
blocks templates export -o templates.json # Templates
```

---

## Concepts

### Block Registry

The `BlockRegistry` contains all language definitions:

```
BlockRegistry
├── Python
│   ├── Test Types: variable, stdout, exist, structural, error, warning, graphics, linting
│   └── Qualifications: verifyEqual, matches, contains, regexp, ...
├── C/C++
│   ├── Test Types: stdout, stderr, exitcode, compile, structural, runtime
│   └── Qualifications: matches, contains, regexp, numericOutput, exitCode, ...
├── Octave/MATLAB
│   ├── Test Types: variable, graphics, stdout, exist, structural
│   └── Qualifications: verifyEqual, matches, contains, regexp, ...
├── R
│   ├── Test Types: variable, stdout, exist, structural
│   └── Qualifications: verifyEqual, matches, contains, regexp, ...
├── Julia
│   ├── Test Types: variable, stdout, exist, structural, error, warning
│   └── Qualifications: verifyEqual, matches, contains, regexp, ...
├── Fortran
│   ├── Test Types: stdout, stderr, exitcode, exist, structural, error, warning
│   └── Qualifications: matches, contains, regexp, numericOutput, exitCode, ...
└── Document
    ├── Test Types: wordcount, linecount, charcount, paragraphcount, sentencecount, ...
    └── Qualifications: (count-based ranges)
```

### Test Types

Each language supports different test types:

| Test Type | Description | Languages |
|-----------|-------------|-----------|
| `variable` | Check variable values | Python, Octave, R |
| `stdout` | Check program stdout | All |
| `stderr` | Check program stderr | C/C++ |
| `exitcode` | Check exit code | C/C++ |
| `compile` | Test compilation | C/C++ |
| `structural` | Check code structure | All |
| `graphics` | Check plot properties | Octave |
| `exist` | Check file exists | All |
| `error` | Expect errors | Python |
| `linting` | Code style checks | Python |
| `runtime` | Execution time/memory | C/C++ |
| `warning` | Expect warnings | Python, Julia, Fortran |
| `wordcount` | Check word count | Document |
| `linecount` | Check line count | Document |
| `section` | Check required sections | Document |
| `keyword` | Check keyword presence | Document |
| `pattern` | Regex pattern matching | Document |

### Qualifications

Qualifications define how values are compared:

| Qualification | Description | Uses Value | Uses Pattern |
|---------------|-------------|------------|--------------|
| `verifyEqual` | Exact match with type checking | ✓ | |
| `matches` | Exact string match | ✓ | |
| `contains` | Substring search | | ✓ |
| `startsWith` | Prefix match | | ✓ |
| `endsWith` | Suffix match | | ✓ |
| `regexp` | Regular expression match | | ✓ |
| `regexpMultiline` | Multiline regex match | | ✓ |
| `numericOutput` | Extract and compare numbers | ✓ | |
| `lineCount` | Count output lines | ✓ | |
| `matchesLine` | Match specific line | ✓ | |
| `containsLine` | Line exists anywhere | ✓ | |
| `exitCode` | Check exit code | ✓ | |
| `count` | Count pattern occurrences | | ✓ |

### Field Types

Fields describe configuration options with these types:

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text value | `"hello"` |
| `number` | Floating-point number | `3.14` |
| `integer` | Whole number | `42` |
| `boolean` | True/false | `true` |
| `array` | List of items | `["a", "b"]` |
| `object` | Nested object | `{key: value}` |
| `enum` | Fixed set of choices | `"gcc"` |
| `pattern` | Regex pattern | `"\\d+"` |
| `code` | Code snippet | `"x = 1"` |
| `filePath` | File path | `"main.c"` |

---

## CLI Commands

### `blocks list`

List available test types and qualifications.

```bash
blocks list              # All languages
blocks list -l python    # Python only
blocks list -l c         # C/C++ only
```

### `blocks init`

Initialize a new test.yaml file with language-appropriate defaults.

```bash
blocks init -l python                           # Create test.yaml for Python
blocks init -l c -n "Calculator Tests"          # With custom name
blocks init -l octave -d "MATLAB tests" -o tests/test.yaml
```

**Options:**
- `-l, --language`: Target language (required)
- `-n, --name`: Test suite name
- `-d, --description`: Test suite description
- `-o, --output`: Output file (default: test.yaml)

### `blocks generate`

Generate a test.yaml snippet for a specific test type.

```bash
blocks generate -l python -t variable -n result
blocks generate -l c -t stdout -q contains -e main.c
blocks generate -l octave -t variable -n x -o test.yaml
```

**Options:**
- `-l, --language`: Target language (required)
- `-t, --test-type`: Test type ID (required)
- `-n, --name`: Test name
- `-c, --collection-name`: Collection name
- `-e, --entry-point`: Entry point file
- `-q, --qualification`: Qualification type
- `-o, --output`: Output file (appends if exists)

### `blocks templates`

Manage pre-built test.yaml templates.

```bash
# List all templates
blocks templates list
blocks templates list -l python
blocks templates list -l c -t stdout

# Show a template
blocks templates show "Variable Check" -l python
blocks templates show "Exit Code" -l c

# Export templates as JSON
blocks templates export -o templates.json
blocks templates export -l python -o python-templates.json
```

### `blocks schema`

Export JSON Schema for validation.

```bash
blocks schema                        # Print to stdout
blocks schema -o schema.json         # Write to file
blocks schema -l python              # Python only
```

### `blocks typescript`

Export TypeScript interfaces.

```bash
blocks typescript                    # Print to stdout
blocks typescript -o types.ts        # Write to file
```

### `blocks data`

Export raw block data as JSON.

```bash
blocks data                          # Print to stdout
blocks data -o data.json             # Write to file
blocks data -l octave                # Octave only
```

### `blocks export`

Export all formats to a directory.

```bash
blocks export ./generated
# Creates:
#   ./generated/blocks.schema.json
#   ./generated/blocks.types.ts
#   ./generated/blocks.data.json

blocks export ./src/types --prefix itp
# Creates:
#   ./src/types/itp.schema.json
#   ./src/types/itp.types.ts
#   ./src/types/itp.data.json
```

---

## Templates Reference

### Python Templates

| Template | Test Type | Description |
|----------|-----------|-------------|
| Variable Check | `variable` | Check a variable's value after running the script |
| Variable with Tolerance | `variable` | Check numeric variable with tolerance |
| Standard Output | `stdout` | Check program prints expected output |
| Output with Input | `stdout` | Check output after providing stdin input |
| File Exists | `exist` | Check that required files exist |
| Structural - Forbidden | `structural` | Forbid certain keywords or functions |
| Structural - Required | `structural` | Require certain keywords or functions |
| Error Expected | `error` | Check that code raises an error |

### C/C++ Templates

| Template | Test Type | Description |
|----------|-----------|-------------|
| Standard Output | `stdout` | Check program stdout |
| Output with Input | `stdout` | Check output after stdin input |
| Numeric Output | `stdout` | Extract and verify numeric values |
| Exit Code | `exitcode` | Verify program exit code |
| Compilation Test | `compile` | Test that code compiles successfully |
| Structural Analysis | `structural` | Check code structure (functions, keywords) |
| Error Output (stderr) | `stderr` | Check stderr output |

### Octave/MATLAB Templates

| Template | Test Type | Description |
|----------|-----------|-------------|
| Variable Check | `variable` | Check workspace variable value |
| Variable with Tolerance | `variable` | Check numeric variable with tolerance |
| Matrix Variable | `variable` | Check matrix/array value |
| Graphics Test | `graphics` | Check plot/figure properties |
| Standard Output | `stdout` | Check console output |
| File Exists | `exist` | Check file exists |
| Structural | `structural` | Check code structure |

### R Templates

| Template | Test Type | Description |
|----------|-----------|-------------|
| Variable Check | `variable` | Check R variable value |
| Numeric with Tolerance | `variable` | Check numeric variable with tolerance |
| Vector Variable | `variable` | Check vector value |
| Standard Output | `stdout` | Check R console output |
| File Exists | `exist` | Check file exists |
| Structural | `structural` | Check code structure |

### Julia Templates

| Template | Test Type | Description |
|----------|-----------|-------------|
| Variable Check | `variable` | Check Julia variable value |
| Variable with Tolerance | `variable` | Check numeric variable with tolerance |
| Standard Output | `stdout` | Check Julia console output |
| File Exists | `exist` | Check file exists |
| Structural | `structural` | Check code structure |
| Error Expected | `error` | Check that code raises an error |

### Fortran Templates

| Template | Test Type | Description |
|----------|-----------|-------------|
| Standard Output | `stdout` | Check program stdout |
| Output with Input | `stdout` | Check output after stdin input |
| Numeric Output | `stdout` | Extract and verify numeric values |
| Exit Code | `exitcode` | Verify program exit code |
| File Exists | `exist` | Check file exists |
| Structural Analysis | `structural` | Check code structure (subroutines, keywords) |

### Document Templates

| Template | Test Type | Description |
|----------|-----------|-------------|
| Word Count | `wordcount` | Check document word count |
| Line Count | `linecount` | Check document line count |
| Required Sections | `section` | Check for required markdown sections |
| Keyword Check | `keyword` | Check for required keywords |
| Forbidden Content | `keyword` | Check that certain content is NOT present |
| Pattern Match | `pattern` | Check for regex pattern matches |
| File Exists | `exist` | Check that required files exist |
| Markdown Structure | `headingcount` | Check markdown document structure |
| Quality Metrics | `uniquewords` | Check vocabulary and sentence quality |
| Paragraph Count | `paragraphcount` | Check number of paragraphs |
| References/Links | `linkcount` | Check for required references |
| Code Examples | `codeblockcount` | Check for code block examples |

---

## Python API

### Getting Blocks

```python
from blocks import (
    get_all_blocks,
    get_language_blocks,
    export_json_schema,
    export_typescript,
)

# Get all blocks
registry = get_all_blocks()
for lang in registry.languages:
    print(f"{lang.name}: {len(lang.test_types)} test types")

# Get specific language
python_blocks = get_language_blocks("python")
c_blocks = get_language_blocks("c")
octave_blocks = get_language_blocks("octave")
r_blocks = get_language_blocks("r")
```

### Generating test.yaml

```python
from blocks import generate_test_yaml, generate_full_test_yaml

# Generate a single test collection
yaml_snippet = generate_test_yaml(
    language="python",
    test_type="variable",
    test_name="result",
    collection_name="Variable Tests",
    qualification="verifyEqual"
)
print(yaml_snippet)
# Output:
# - name: Variable Tests
#   type: variable
#   entryPoint: solution.py
#   tests:
#   - name: result
#     qualification: verifyEqual

# Generate a complete test.yaml file
full_yaml = generate_full_test_yaml(
    language="c",
    name="Calculator Tests",
    description="Test the calculator program"
)
print(full_yaml)
# Output:
# name: Calculator Tests
# description: Test the calculator program
# version: '1.0'
# properties:
#   timeout: 30.0
#   compiler: gcc
#   compilerFlags:
#   - -Wall
#   - -Wextra
#   tests: []
```

### Working with Templates

```python
from blocks import get_templates, get_templates_by_test_type, export_templates_json

# Get all templates
all_templates = get_templates()

# Get templates for a specific language
python_templates = get_templates("python")
c_templates = get_templates("c")

# Get templates for a specific test type
stdout_templates = get_templates_by_test_type("c", "stdout")

# Use a template
for t in python_templates:
    print(f"{t.name} ({t.test_type}):")
    print(t.yaml_snippet)
    print(f"Placeholders: {t.placeholders}")
    print()

# Export all templates as JSON
json_str = export_templates_json()
export_templates_json("templates.json")  # Write to file
```

### Inspecting Blocks

```python
from blocks import get_language_blocks

python = get_language_blocks("python")

# List test types
for tt in python.test_types:
    print(f"Test Type: {tt.id}")
    print(f"  Description: {tt.description}")
    print(f"  Qualifications: {tt.qualifications}")
    print(f"  Collection Fields: {[f.name for f in tt.collection_fields]}")
    print(f"  Test Fields: {[f.name for f in tt.test_fields]}")

# List qualifications
for qual in python.qualifications:
    print(f"Qualification: {qual.id}")
    print(f"  Uses Value: {qual.uses_value}")
    print(f"  Uses Pattern: {qual.uses_pattern}")
```

### Exporting Schemas

```python
from blocks import export_json_schema, export_typescript

# Export JSON Schema
schema_json = export_json_schema()
export_json_schema("blocks.schema.json")

# Export TypeScript
ts_code = export_typescript()
export_typescript("blocks.types.ts")
```

---

## VSCode Extension Integration

### Loading Blocks and Templates

```typescript
import { BlockRegistry, LanguageBlocks, TestTypeBlock, TestTemplate } from './blocks.types';
import blocksData from './blocks.data.json';
import templatesData from './templates.json';

// Cast imported JSON to typed registry
const registry: BlockRegistry = blocksData as BlockRegistry;
const templates: { version: string; templates: TestTemplate[] } = templatesData;

// Find language by file extension
function getLanguageForFile(filename: string): LanguageBlocks | undefined {
  const ext = '.' + filename.split('.').pop();
  return registry.languages.find(lang =>
    lang.fileExtensions.includes(ext)
  );
}

// Get test types for language
function getTestTypes(langId: string): TestTypeBlock[] {
  const lang = registry.languages.find(l => l.id === langId);
  return lang?.testTypes ?? [];
}

// Get templates for language
function getTemplatesForLanguage(langId: string): TestTemplate[] {
  return templates.templates.filter(t => t.language === langId);
}
```

### Building a Test Creation Form

```typescript
import { FieldDefinition } from './blocks.types';

// Get fields for test type
function getFieldsForTestType(
  langId: string,
  testTypeId: string
): { collection: FieldDefinition[], test: FieldDefinition[] } {
  const lang = registry.languages.find(l => l.id === langId);
  const testType = lang?.testTypes.find(t => t.id === testTypeId);
  return {
    collection: testType?.collectionFields ?? [],
    test: testType?.testFields ?? []
  };
}

// Generate form inputs based on field definitions
function renderFormField(field: FieldDefinition): string {
  switch (field.type) {
    case 'boolean':
      return `<input type="checkbox" name="${field.name}" />`;
    case 'number':
    case 'integer':
      return `<input type="number" name="${field.name}"
        min="${field.minValue}" max="${field.maxValue}"
        value="${field.default ?? ''}" />`;
    case 'enum':
      return `<select name="${field.name}">
        ${field.enumValues?.map(v =>
          `<option value="${v}" ${v === field.default ? 'selected' : ''}>${v}</option>`
        ).join('')}
      </select>`;
    case 'array':
      return `<textarea name="${field.name}"
        placeholder="${field.placeholder ?? 'One item per line'}"></textarea>`;
    case 'code':
      return `<textarea name="${field.name}" class="code-editor"
        placeholder="${field.placeholder ?? ''}"></textarea>`;
    case 'filePath':
      return `<input type="text" name="${field.name}"
        placeholder="${field.placeholder ?? 'path/to/file'}" />`;
    case 'pattern':
      return `<input type="text" name="${field.name}"
        placeholder="${field.placeholder ?? 'regex pattern'}" class="monospace" />`;
    default:
      return `<input type="text" name="${field.name}"
        placeholder="${field.placeholder ?? ''}"
        value="${field.default ?? ''}" />`;
  }
}
```

### Inserting Templates

```typescript
// Insert a template's YAML snippet
function insertTemplate(template: TestTemplate): void {
  let yaml = template.yaml_snippet;

  // Optionally replace placeholders with user values
  for (const [placeholder, description] of Object.entries(template.placeholders)) {
    const userValue = prompt(`Enter ${description}:`, placeholder);
    if (userValue) {
      yaml = yaml.replace(placeholder, userValue);
    }
  }

  // Insert into editor
  insertIntoEditor(yaml);
}

// Get qualifications for a test type
function getQualificationsForTestType(
  langId: string,
  testTypeId: string
): string[] {
  const lang = registry.languages.find(l => l.id === langId);
  const testType = lang?.testTypes.find(t => t.id === testTypeId);
  return testType?.qualifications ?? [];
}
```

---

## Adding New Languages

To add a new language, create a function in `models.py`:

```python
def get_rust_blocks() -> LanguageBlocks:
    return LanguageBlocks(
        id="rust",
        name="Rust",
        description="Rust programming language",
        file_extensions=[".rs"],
        icon="rust",
        qualifications=[
            COMMON_QUALIFICATIONS["matches"],
            COMMON_QUALIFICATIONS["contains"],
            COMMON_QUALIFICATIONS["regexp"],
            COMMON_QUALIFICATIONS["exitCode"],
        ],
        test_types=[
            TestTypeBlock(
                id="stdout",
                name="Standard Output",
                description="Check program stdout",
                qualifications=["matches", "contains", "regexp"],
                default_qualification="contains",
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["timeout"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["pattern"],
                    COMMON_FIELDS["qualification"],
                ],
            ),
            # ... more test types
        ],
        defaults={
            "timeout": 30.0,
            "compiler": "rustc",
        }
    )
```

Then add it to `get_all_blocks()`:

```python
def get_all_blocks() -> BlockRegistry:
    return BlockRegistry(
        version="1.0",
        languages=[
            get_python_blocks(),
            get_c_blocks(),
            get_octave_blocks(),
            get_r_blocks(),
            get_rust_blocks(),  # Add new language
        ]
    )
```

And add templates in a new function:

```python
def get_rust_templates() -> List[TestTemplate]:
    return [
        TestTemplate(
            name="Standard Output",
            description="Check program stdout",
            language="rust",
            test_type="stdout",
            yaml_snippet="""- name: "Output Tests"
  type: stdout
  entryPoint: main.rs
  tests:
    - name: output
      qualification: contains
      pattern: "Hello"
""",
            placeholders={
                "main.rs": "Source file",
                "Hello": "Expected output",
            }
        ),
    ]
```

Update `get_templates()` to include the new language.

---

## Data Structures

### LanguageBlocks

```python
class LanguageBlocks(BaseModel):
    id: str                          # e.g., "python"
    name: str                        # e.g., "Python"
    description: str
    file_extensions: List[str]       # e.g., [".py"]
    icon: Optional[str]
    test_types: List[TestTypeBlock]
    qualifications: List[QualificationBlock]
    config_fields: List[FieldDefinition]
    defaults: Dict[str, Any]
```

### TestTypeBlock

```python
class TestTypeBlock(BaseModel):
    id: str                          # e.g., "variable"
    name: str                        # e.g., "Variable"
    description: str
    icon: Optional[str]
    category: str                    # output, variable, structure, compilation
    qualifications: List[str]        # List of qualification IDs
    default_qualification: Optional[str]
    collection_fields: List[FieldDefinition]
    test_fields: List[FieldDefinition]
    example: Optional[Dict[str, Any]]
```

### QualificationBlock

```python
class QualificationBlock(BaseModel):
    id: str                          # e.g., "verifyEqual"
    name: str                        # e.g., "Verify Equal"
    description: str
    category: str                    # comparison, pattern, numeric, structural
    uses_value: bool
    uses_pattern: bool
    uses_tolerance: bool
    uses_line_number: bool
    uses_count: bool
    extra_fields: List[FieldDefinition]
    example: Optional[Dict[str, Any]]
```

### FieldDefinition

```python
class FieldDefinition(BaseModel):
    name: str                        # e.g., "timeout"
    type: FieldType                  # string, number, boolean, etc.
    description: str
    required: bool
    default: Optional[Any]
    enum_values: Optional[List[str]]
    array_item_type: Optional[FieldType]
    min_value: Optional[float]
    max_value: Optional[float]
    min_length: Optional[int]
    max_length: Optional[int]
    pattern: Optional[str]
    placeholder: Optional[str]
    examples: Optional[List[Any]]
```

### TestTemplate

```python
class TestTemplate(BaseModel):
    name: str                        # e.g., "Variable Check"
    description: str                 # e.g., "Check a variable's value"
    language: str                    # e.g., "python"
    test_type: str                   # e.g., "variable"
    yaml_snippet: str                # Ready-to-use YAML
    placeholders: Dict[str, str]     # Placeholders and descriptions
```

---

## Complete Example: Creating a test.yaml

### Using CLI

```bash
# 1. Initialize test.yaml
blocks init -l c -n "Calculator Tests" -d "Test the calculator program"

# 2. Add test collections using templates
blocks templates show "Output with Input" -l c
# Copy the YAML snippet and customize it

# 3. Or generate programmatically
blocks generate -l c -t stdout -n sum_check -c "Addition Test" -e calculator.c -q contains
```

### Using Python API

```python
from blocks import generate_full_test_yaml, generate_test_yaml
import yaml

# Generate base structure
base = yaml.safe_load(generate_full_test_yaml(
    language="c",
    name="Calculator Tests",
    description="Test the calculator program"
))

# Add test collections
collections = []

# Test 1: Basic addition
collections.append({
    "name": "Basic Addition",
    "type": "stdout",
    "entryPoint": "calculator.c",
    "inputAnswers": ["5", "3"],
    "tests": [
        {"name": "sum", "qualification": "contains", "pattern": "Sum: 8"},
        {"name": "diff", "qualification": "contains", "pattern": "Difference: 2"},
    ]
})

# Test 2: Exit code
collections.append({
    "name": "Exit Code",
    "type": "exitcode",
    "entryPoint": "calculator.c",
    "inputAnswers": ["5", "3"],
    "tests": [
        {"name": "success", "expectedExitCode": 0}
    ]
})

# Test 3: Structural
collections.append({
    "name": "Code Structure",
    "type": "structural",
    "entryPoint": "calculator.c",
    "tests": [
        {"name": "main"},
        {"name": "scanf", "allowedOccuranceRange": [2, 10]},
        {"name": "printf", "allowedOccuranceRange": [4, 20]},
    ]
})

base["properties"]["tests"] = collections

# Write to file
with open("test.yaml", "w") as f:
    yaml.dump(base, f, default_flow_style=False, sort_keys=False)
```

### Result: test.yaml

```yaml
name: Calculator Tests
description: Test the calculator program
version: '1.0'
properties:
  timeout: 30.0
  compiler: gcc
  compilerFlags:
  - -Wall
  - -Wextra
  tests:
  - name: Basic Addition
    type: stdout
    entryPoint: calculator.c
    inputAnswers:
    - '5'
    - '3'
    tests:
    - name: sum
      qualification: contains
      pattern: 'Sum: 8'
    - name: diff
      qualification: contains
      pattern: 'Difference: 2'
  - name: Exit Code
    type: exitcode
    entryPoint: calculator.c
    inputAnswers:
    - '5'
    - '3'
    tests:
    - name: success
      expectedExitCode: 0
  - name: Code Structure
    type: structural
    entryPoint: calculator.c
    tests:
    - name: main
    - name: scanf
      allowedOccuranceRange: [2, 10]
    - name: printf
      allowedOccuranceRange: [4, 20]
```

---

## See Also

- [ctcore/models.py](../ctcore/models.py) - Core test data models
- [ctcore/stdio.py](../ctcore/stdio.py) - Stdio comparison utilities
- [testers/](../testers/) - Unified testing framework (all languages)
- [ctexec/](../ctexec/) - Execution backends (interpreted & compiled)
