"""
Computor Testing Framework - Test Block Models

Pydantic models that define the structure of test cases for each language.
These are designed to be exported to JSON Schema and TypeScript for VSCode.
"""

import json
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


# =============================================================================
# Field Types
# =============================================================================

class FieldType(str, Enum):
    """Data types for test configuration fields"""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    ENUM = "enum"
    PATTERN = "pattern"      # Regex pattern
    CODE = "code"            # Code snippet
    FILE_PATH = "filePath"   # File path


class FieldDefinition(BaseModel):
    """Definition of a single configuration field"""
    name: str = Field(description="Field name (camelCase)")
    type: FieldType = Field(description="Data type")
    description: str = Field(description="Human-readable description")
    required: bool = Field(default=False, description="Is this field required?")
    default: Optional[Any] = Field(default=None, description="Default value")
    enum_values: Optional[List[str]] = Field(default=None, description="Allowed values for enum type")
    array_item_type: Optional[FieldType] = Field(default=None, description="Item type for arrays")
    min_value: Optional[float] = Field(default=None, description="Minimum value for numbers")
    max_value: Optional[float] = Field(default=None, description="Maximum value for numbers")
    min_length: Optional[int] = Field(default=None, description="Minimum length for strings/arrays")
    max_length: Optional[int] = Field(default=None, description="Maximum length for strings/arrays")
    pattern: Optional[str] = Field(default=None, description="Regex pattern for validation")
    placeholder: Optional[str] = Field(default=None, description="Placeholder text for UI")
    examples: Optional[List[Any]] = Field(default=None, description="Example values")

    class Config:
        use_enum_values = True


# =============================================================================
# Qualification Blocks
# =============================================================================

class QualificationBlock(BaseModel):
    """Definition of a qualification/comparison type"""
    id: str = Field(description="Unique identifier (e.g., 'verifyEqual')")
    name: str = Field(description="Display name (e.g., 'Verify Equal')")
    description: str = Field(description="What this qualification does")
    category: str = Field(default="comparison", description="Category: comparison, pattern, numeric, structural")

    # Which fields are used with this qualification
    uses_value: bool = Field(default=False, description="Uses 'value' field for expected value")
    uses_pattern: bool = Field(default=False, description="Uses 'pattern' field for matching")
    uses_tolerance: bool = Field(default=False, description="Uses numeric tolerance fields")
    uses_line_number: bool = Field(default=False, description="Uses line number field")
    uses_count: bool = Field(default=False, description="Uses count/range fields")

    # Additional fields specific to this qualification
    extra_fields: List[FieldDefinition] = Field(default=[], description="Additional fields")

    # Example usage
    example: Optional[Dict[str, Any]] = Field(default=None, description="Example configuration")


# =============================================================================
# Test Type Blocks
# =============================================================================

class TestTypeBlock(BaseModel):
    """Definition of a test type (e.g., stdout, variable, structural)"""
    id: str = Field(description="Unique identifier (e.g., 'stdout')")
    name: str = Field(description="Display name (e.g., 'Standard Output')")
    description: str = Field(description="What this test type checks")
    icon: Optional[str] = Field(default=None, description="Icon name for UI")
    category: str = Field(default="output", description="Category: output, variable, structure, compilation")

    # Supported qualifications for this test type
    qualifications: List[str] = Field(description="List of qualification IDs supported")
    default_qualification: Optional[str] = Field(default=None, description="Default qualification")

    # Fields available at collection level (test group)
    collection_fields: List[FieldDefinition] = Field(default=[], description="Fields for test collection")

    # Fields available at individual test level
    test_fields: List[FieldDefinition] = Field(default=[], description="Fields for individual tests")

    # Example configuration
    example: Optional[Dict[str, Any]] = Field(default=None, description="Example test.yaml snippet")


# =============================================================================
# Language Blocks
# =============================================================================

class LanguageBlocks(BaseModel):
    """All test blocks available for a programming language"""
    id: str = Field(description="Language identifier (e.g., 'python', 'c')")
    name: str = Field(description="Display name (e.g., 'Python', 'C/C++')")
    description: str = Field(description="Language description")
    file_extensions: List[str] = Field(description="File extensions (e.g., ['.py'])")
    icon: Optional[str] = Field(default=None, description="Icon name for UI")

    # Available test types for this language
    test_types: List[TestTypeBlock] = Field(description="Available test types")

    # Available qualifications for this language
    qualifications: List[QualificationBlock] = Field(description="Available qualifications")

    # Language-specific configuration fields
    config_fields: List[FieldDefinition] = Field(default=[], description="Language-specific config")

    # Default values
    defaults: Dict[str, Any] = Field(default={}, description="Default configuration values")


class BlockRegistry(BaseModel):
    """Registry of all language blocks"""
    version: str = Field(default="1.0", description="Schema version")
    languages: List[LanguageBlocks] = Field(description="All language definitions")


# =============================================================================
# Common Field Definitions (reusable)
# =============================================================================

# Common fields used across multiple test types
COMMON_FIELDS = {
    "name": FieldDefinition(
        name="name",
        type=FieldType.STRING,
        description="Test name (displayed in results)",
        required=True,
        placeholder="e.g., check_sum_result"
    ),
    "value": FieldDefinition(
        name="value",
        type=FieldType.STRING,
        description="Expected value to compare against",
        required=False,
        placeholder="Expected output or value"
    ),
    "pattern": FieldDefinition(
        name="pattern",
        type=FieldType.PATTERN,
        description="Pattern for matching (string or regex)",
        required=False,
        placeholder="e.g., Sum: \\d+"
    ),
    "qualification": FieldDefinition(
        name="qualification",
        type=FieldType.ENUM,
        description="Comparison method",
        required=False,
        default="verifyEqual"
    ),
    "timeout": FieldDefinition(
        name="timeout",
        type=FieldType.NUMBER,
        description="Maximum execution time in seconds",
        required=False,
        default=30.0,
        min_value=0.1,
        max_value=600
    ),
    "entryPoint": FieldDefinition(
        name="entryPoint",
        type=FieldType.FILE_PATH,
        description="Main file to execute",
        required=False,
        placeholder="e.g., main.py"
    ),
    "inputAnswers": FieldDefinition(
        name="inputAnswers",
        type=FieldType.ARRAY,
        array_item_type=FieldType.STRING,
        description="Input lines to send to stdin",
        required=False,
        examples=[["5", "3"], ["yes"]]
    ),
    "ignoreCase": FieldDefinition(
        name="ignoreCase",
        type=FieldType.BOOLEAN,
        description="Ignore case when comparing",
        required=False,
        default=False
    ),
    "trimOutput": FieldDefinition(
        name="trimOutput",
        type=FieldType.BOOLEAN,
        description="Trim whitespace from output",
        required=False,
        default=True
    ),
    "relativeTolerance": FieldDefinition(
        name="relativeTolerance",
        type=FieldType.NUMBER,
        description="Relative tolerance for numeric comparison",
        required=False,
        default=1e-12,
        min_value=0
    ),
    "absoluteTolerance": FieldDefinition(
        name="absoluteTolerance",
        type=FieldType.NUMBER,
        description="Absolute tolerance for numeric comparison",
        required=False,
        default=0.0001,
        min_value=0
    ),
    "allowedOccuranceRange": FieldDefinition(
        name="allowedOccuranceRange",
        type=FieldType.ARRAY,
        array_item_type=FieldType.INTEGER,
        description="Allowed occurrence count [min, max]",
        required=False,
        min_length=2,
        max_length=2,
        examples=[[1, 5], [0, 0]]
    ),
    "allowEmpty": FieldDefinition(
        name="allowEmpty",
        type=FieldType.BOOLEAN,
        description="For exist tests: if False (default), fail if file is empty (0 bytes)",
        required=False,
        default=False
    ),
}


# =============================================================================
# Common Qualifications (reusable)
# =============================================================================

COMMON_QUALIFICATIONS = {
    "verifyEqual": QualificationBlock(
        id="verifyEqual",
        name="Verify Equal",
        description="Exact value comparison with type checking",
        category="comparison",
        uses_value=True,
        uses_tolerance=True,
        example={"qualification": "verifyEqual", "value": 42}
    ),
    "matches": QualificationBlock(
        id="matches",
        name="Matches",
        description="Exact string match",
        category="comparison",
        uses_value=True,
        example={"qualification": "matches", "value": "Hello, World!"}
    ),
    "contains": QualificationBlock(
        id="contains",
        name="Contains",
        description="Check if output contains substring",
        category="pattern",
        uses_pattern=True,
        example={"qualification": "contains", "pattern": "Success"}
    ),
    "startsWith": QualificationBlock(
        id="startsWith",
        name="Starts With",
        description="Check if output starts with prefix",
        category="pattern",
        uses_pattern=True,
        example={"qualification": "startsWith", "pattern": "Result:"}
    ),
    "endsWith": QualificationBlock(
        id="endsWith",
        name="Ends With",
        description="Check if output ends with suffix",
        category="pattern",
        uses_pattern=True,
        example={"qualification": "endsWith", "pattern": "done."}
    ),
    "regexp": QualificationBlock(
        id="regexp",
        name="Regular Expression",
        description="Match against regular expression",
        category="pattern",
        uses_pattern=True,
        example={"qualification": "regexp", "pattern": "Result: \\d+\\.\\d{2}"}
    ),
    "regexpMultiline": QualificationBlock(
        id="regexpMultiline",
        name="Multiline Regex",
        description="Multiline regular expression matching",
        category="pattern",
        uses_pattern=True,
        example={"qualification": "regexpMultiline", "pattern": "Start.*End"}
    ),
    "numericOutput": QualificationBlock(
        id="numericOutput",
        name="Numeric Output",
        description="Extract and compare numeric values from output",
        category="numeric",
        uses_value=True,
        uses_tolerance=True,
        example={"qualification": "numericOutput", "value": 3.14159, "numericTolerance": 0.001}
    ),
    "lineCount": QualificationBlock(
        id="lineCount",
        name="Line Count",
        description="Check number of output lines",
        category="structural",
        uses_value=True,
        example={"qualification": "lineCount", "value": 5}
    ),
    "matchesLine": QualificationBlock(
        id="matchesLine",
        name="Matches Line",
        description="Match specific line number",
        category="pattern",
        uses_value=True,
        uses_line_number=True,
        example={"qualification": "matchesLine", "value": "Header", "lineNumber": 1}
    ),
    "containsLine": QualificationBlock(
        id="containsLine",
        name="Contains Line",
        description="Check if line exists anywhere in output",
        category="pattern",
        uses_value=True,
        example={"qualification": "containsLine", "value": "Test passed"}
    ),
    "count": QualificationBlock(
        id="count",
        name="Count Occurrences",
        description="Count occurrences of pattern",
        category="structural",
        uses_pattern=True,
        uses_count=True,
        example={"qualification": "count", "pattern": "error", "allowedOccuranceRange": [0, 0]}
    ),
    "exitCode": QualificationBlock(
        id="exitCode",
        name="Exit Code",
        description="Check program exit code",
        category="comparison",
        uses_value=True,
        example={"qualification": "exitCode", "value": 0}
    ),
}


# =============================================================================
# Language-Specific Block Definitions
# =============================================================================

def get_python_blocks() -> LanguageBlocks:
    """Get test blocks for Python"""
    return LanguageBlocks(
        id="python",
        name="Python",
        description="Python programming language",
        file_extensions=[".py"],
        icon="python",
        qualifications=[
            COMMON_QUALIFICATIONS["verifyEqual"],
            COMMON_QUALIFICATIONS["matches"],
            COMMON_QUALIFICATIONS["contains"],
            COMMON_QUALIFICATIONS["startsWith"],
            COMMON_QUALIFICATIONS["endsWith"],
            COMMON_QUALIFICATIONS["regexp"],
            COMMON_QUALIFICATIONS["numericOutput"],
            COMMON_QUALIFICATIONS["count"],
        ],
        test_types=[
            TestTypeBlock(
                id="variable",
                name="Variable",
                description="Check variable values after execution",
                icon="variable",
                category="variable",
                qualifications=["verifyEqual", "matches", "contains", "regexp"],
                default_qualification="verifyEqual",
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["timeout"],
                    COMMON_FIELDS["inputAnswers"],
                    FieldDefinition(
                        name="setUpCode",
                        type=FieldType.ARRAY,
                        array_item_type=FieldType.CODE,
                        description="Code to run before tests",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["value"],
                    COMMON_FIELDS["qualification"],
                    COMMON_FIELDS["relativeTolerance"],
                    COMMON_FIELDS["absoluteTolerance"],
                    FieldDefinition(
                        name="evalString",
                        type=FieldType.CODE,
                        description="Expression to evaluate for expected value",
                        required=False,
                        placeholder="e.g., len(result)"
                    ),
                ],
                example={
                    "name": "Variable Tests",
                    "type": "variable",
                    "entryPoint": "solution.py",
                    "tests": [
                        {"name": "result", "qualification": "verifyEqual"},
                        {"name": "total", "value": 100}
                    ]
                }
            ),
            TestTypeBlock(
                id="stdout",
                name="Standard Output",
                description="Check program stdout",
                icon="terminal",
                category="output",
                qualifications=["matches", "contains", "startsWith", "endsWith", "regexp", "numericOutput", "lineCount"],
                default_qualification="contains",
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["timeout"],
                    COMMON_FIELDS["inputAnswers"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["value"],
                    COMMON_FIELDS["pattern"],
                    COMMON_FIELDS["qualification"],
                    COMMON_FIELDS["ignoreCase"],
                    COMMON_FIELDS["trimOutput"],
                ],
                example={
                    "name": "Output Tests",
                    "type": "stdout",
                    "entryPoint": "hello.py",
                    "tests": [
                        {"name": "greeting", "qualification": "contains", "pattern": "Hello"}
                    ]
                }
            ),
            TestTypeBlock(
                id="exist",
                name="File Exists",
                description="Check if file exists (and optionally not empty)",
                icon="file",
                category="structure",
                qualifications=[],
                collection_fields=[
                    FieldDefinition(
                        name="file",
                        type=FieldType.FILE_PATH,
                        description="Directory to check in",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],  # name is the file pattern
                    COMMON_FIELDS["allowEmpty"],
                ],
                example={
                    "name": "File Existence",
                    "type": "exist",
                    "tests": [
                        {"name": "solution.py"},
                        {"name": "*.csv"},
                        {"name": "output.txt", "allowEmpty": True}
                    ]
                }
            ),
            TestTypeBlock(
                id="structural",
                name="Structural",
                description="Check code structure (keywords, functions)",
                icon="code",
                category="structure",
                qualifications=["count"],
                collection_fields=[
                    FieldDefinition(
                        name="file",
                        type=FieldType.FILE_PATH,
                        description="File to analyze",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],  # name is the keyword/construct
                    COMMON_FIELDS["allowedOccuranceRange"],
                    FieldDefinition(
                        name="occuranceType",
                        type=FieldType.ENUM,
                        description="Token type to match",
                        enum_values=["NAME", "KEYWORD", "OP"],
                        required=False
                    ),
                ],
                example={
                    "name": "Code Structure",
                    "type": "structural",
                    "tests": [
                        {"name": "for", "allowedOccuranceRange": [1, 5]},
                        {"name": "eval", "allowedOccuranceRange": [0, 0]}
                    ]
                }
            ),
            TestTypeBlock(
                id="error",
                name="Error",
                description="Check for expected errors",
                icon="error",
                category="output",
                qualifications=["regexp", "contains"],
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["inputAnswers"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["pattern"],
                ],
                example={
                    "name": "Error Handling",
                    "type": "error",
                    "tests": [
                        {"name": "raises_error"},
                        {"name": "specific_error", "pattern": "ValueError"}
                    ]
                }
            ),
            TestTypeBlock(
                id="warning",
                name="Warning",
                description="Check for expected warnings",
                icon="warning",
                category="output",
                qualifications=["regexp", "contains"],
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["inputAnswers"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["pattern"],
                ],
                example={
                    "name": "Warning Check",
                    "type": "warning",
                    "tests": [
                        {"name": "deprecation_warning", "pattern": "DeprecationWarning"}
                    ]
                }
            ),
            TestTypeBlock(
                id="graphics",
                name="Graphics",
                description="Check matplotlib plot/figure properties",
                icon="chart",
                category="variable",
                qualifications=["verifyEqual"],
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["timeout"],
                    COMMON_FIELDS["inputAnswers"],
                    FieldDefinition(
                        name="storeGraphicsArtifacts",
                        type=FieldType.BOOLEAN,
                        description="Save figure images as artifacts",
                        required=False,
                        default=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["value"],
                    COMMON_FIELDS["relativeTolerance"],
                ],
                example={
                    "name": "Plot Tests",
                    "type": "graphics",
                    "entryPoint": "plot_data.py",
                    "tests": [
                        {"name": "gcf().axes[0].get_xlabel()", "value": "Time"},
                        {"name": "gcf().axes[0].get_title()", "value": "Data Plot"}
                    ]
                }
            ),
            TestTypeBlock(
                id="linting",
                name="Linting",
                description="Check code style with flake8/pylint",
                icon="lint",
                category="structure",
                qualifications=[],
                collection_fields=[
                    FieldDefinition(
                        name="file",
                        type=FieldType.FILE_PATH,
                        description="File to lint",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    FieldDefinition(
                        name="pattern",
                        type=FieldType.STRING,
                        description="Error codes to ignore (e.g., 'E501,W503')",
                        required=False
                    ),
                ],
                example={
                    "name": "Code Style",
                    "type": "linting",
                    "tests": [
                        {"name": "pep8_compliant", "pattern": "E501"}
                    ]
                }
            ),
        ],
        defaults={
            "timeout": 30.0,
            "relativeTolerance": 1e-12,
            "absoluteTolerance": 0.0001,
        }
    )


def get_c_blocks() -> LanguageBlocks:
    """Get test blocks for C/C++"""
    return LanguageBlocks(
        id="c",
        name="C/C++",
        description="C and C++ programming languages",
        file_extensions=[".c", ".cpp", ".cxx", ".cc", ".h", ".hpp"],
        icon="c",
        qualifications=[
            COMMON_QUALIFICATIONS["matches"],
            COMMON_QUALIFICATIONS["contains"],
            COMMON_QUALIFICATIONS["startsWith"],
            COMMON_QUALIFICATIONS["endsWith"],
            COMMON_QUALIFICATIONS["regexp"],
            COMMON_QUALIFICATIONS["regexpMultiline"],
            COMMON_QUALIFICATIONS["numericOutput"],
            COMMON_QUALIFICATIONS["lineCount"],
            COMMON_QUALIFICATIONS["matchesLine"],
            COMMON_QUALIFICATIONS["containsLine"],
            COMMON_QUALIFICATIONS["exitCode"],
            COMMON_QUALIFICATIONS["count"],
        ],
        test_types=[
            TestTypeBlock(
                id="stdout",
                name="Standard Output",
                description="Check program stdout",
                icon="terminal",
                category="output",
                qualifications=["matches", "contains", "startsWith", "endsWith", "regexp", "numericOutput", "lineCount", "matchesLine", "containsLine"],
                default_qualification="contains",
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["timeout"],
                    COMMON_FIELDS["inputAnswers"],
                    FieldDefinition(
                        name="compiler",
                        type=FieldType.ENUM,
                        description="Compiler to use",
                        enum_values=["gcc", "g++", "clang", "clang++"],
                        required=False,
                        default="gcc"
                    ),
                    FieldDefinition(
                        name="compilerFlags",
                        type=FieldType.ARRAY,
                        array_item_type=FieldType.STRING,
                        description="Compiler flags",
                        required=False,
                        examples=[["-Wall", "-O2"], ["-std=c11"]]
                    ),
                    FieldDefinition(
                        name="args",
                        type=FieldType.ARRAY,
                        array_item_type=FieldType.STRING,
                        description="Command line arguments",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["value"],
                    COMMON_FIELDS["pattern"],
                    COMMON_FIELDS["qualification"],
                    COMMON_FIELDS["ignoreCase"],
                    COMMON_FIELDS["trimOutput"],
                    FieldDefinition(
                        name="lineNumber",
                        type=FieldType.INTEGER,
                        description="Line number to check (1-indexed)",
                        required=False,
                        min_value=1
                    ),
                    FieldDefinition(
                        name="numericTolerance",
                        type=FieldType.NUMBER,
                        description="Tolerance for numeric comparison",
                        required=False,
                        default=1e-6
                    ),
                ],
                example={
                    "name": "Output Tests",
                    "type": "stdout",
                    "entryPoint": "main.c",
                    "inputAnswers": ["5", "3"],
                    "tests": [
                        {"name": "sum", "qualification": "contains", "pattern": "Sum: 8"},
                        {"name": "numeric", "qualification": "numericOutput", "value": 8}
                    ]
                }
            ),
            TestTypeBlock(
                id="stderr",
                name="Standard Error",
                description="Check program stderr",
                icon="error",
                category="output",
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
                example={
                    "name": "Error Output",
                    "type": "stderr",
                    "entryPoint": "program.c",
                    "tests": [
                        {"name": "error_msg", "qualification": "contains", "pattern": "Error:"}
                    ]
                }
            ),
            TestTypeBlock(
                id="exitcode",
                name="Exit Code",
                description="Check program exit code",
                icon="exit",
                category="output",
                qualifications=["exitCode"],
                default_qualification="exitCode",
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["inputAnswers"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    FieldDefinition(
                        name="expectedExitCode",
                        type=FieldType.INTEGER,
                        description="Expected exit code",
                        required=False,
                        default=0
                    ),
                ],
                example={
                    "name": "Exit Code",
                    "type": "exitcode",
                    "entryPoint": "program.c",
                    "tests": [
                        {"name": "success", "expectedExitCode": 0},
                        {"name": "error", "expectedExitCode": 1}
                    ]
                }
            ),
            TestTypeBlock(
                id="compile",
                name="Compilation",
                description="Test compilation success/failure",
                icon="build",
                category="compilation",
                qualifications=["regexp"],
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    FieldDefinition(
                        name="compiler",
                        type=FieldType.ENUM,
                        description="Compiler to use",
                        enum_values=["gcc", "g++", "clang", "clang++"],
                        required=False
                    ),
                    FieldDefinition(
                        name="compilerFlags",
                        type=FieldType.ARRAY,
                        array_item_type=FieldType.STRING,
                        description="Compiler flags",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    FieldDefinition(
                        name="value",
                        type=FieldType.BOOLEAN,
                        description="Expect compilation to succeed (true) or fail (false)",
                        required=False,
                        default=True
                    ),
                    COMMON_FIELDS["pattern"],  # For checking compiler messages
                ],
                example={
                    "name": "Compilation",
                    "type": "compile",
                    "entryPoint": "program.c",
                    "compilerFlags": ["-Wall", "-Werror"],
                    "tests": [
                        {"name": "compiles", "value": True},
                        {"name": "no_warnings", "pattern": "warning:"}
                    ]
                }
            ),
            TestTypeBlock(
                id="structural",
                name="Structural",
                description="Check code structure",
                icon="code",
                category="structure",
                qualifications=["count"],
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],  # Keyword or pattern to find
                    COMMON_FIELDS["allowedOccuranceRange"],
                    COMMON_FIELDS["pattern"],
                ],
                example={
                    "name": "Structure",
                    "type": "structural",
                    "entryPoint": "program.c",
                    "tests": [
                        {"name": "main"},
                        {"name": "malloc", "allowedOccuranceRange": [0, 0]},
                        {"name": "for", "allowedOccuranceRange": [1, 10]}
                    ]
                }
            ),
            TestTypeBlock(
                id="runtime",
                name="Runtime",
                description="Check execution time/memory",
                icon="timer",
                category="output",
                qualifications=[],
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["inputAnswers"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    FieldDefinition(
                        name="value",
                        type=FieldType.NUMBER,
                        description="Maximum execution time in seconds",
                        required=False
                    ),
                ],
                example={
                    "name": "Performance",
                    "type": "runtime",
                    "entryPoint": "algorithm.c",
                    "tests": [
                        {"name": "fast_execution", "value": 1.0}
                    ]
                }
            ),
        ],
        config_fields=[
            FieldDefinition(
                name="compiler",
                type=FieldType.ENUM,
                description="Default compiler",
                enum_values=["gcc", "g++", "clang", "clang++"],
                default="gcc"
            ),
            FieldDefinition(
                name="compilerFlags",
                type=FieldType.ARRAY,
                array_item_type=FieldType.STRING,
                description="Default compiler flags",
                default=["-Wall", "-Wextra"]
            ),
        ],
        defaults={
            "timeout": 30.0,
            "compiler": "gcc",
            "compilerFlags": ["-Wall", "-Wextra"],
        }
    )


def get_octave_blocks() -> LanguageBlocks:
    """Get test blocks for Octave/MATLAB"""
    return LanguageBlocks(
        id="octave",
        name="Octave/MATLAB",
        description="GNU Octave and MATLAB",
        file_extensions=[".m"],
        icon="matlab",
        qualifications=[
            COMMON_QUALIFICATIONS["verifyEqual"],
            COMMON_QUALIFICATIONS["matches"],
            COMMON_QUALIFICATIONS["contains"],
            COMMON_QUALIFICATIONS["regexp"],
            COMMON_QUALIFICATIONS["count"],
        ],
        test_types=[
            TestTypeBlock(
                id="variable",
                name="Variable",
                description="Check workspace variable values",
                icon="variable",
                category="variable",
                qualifications=["verifyEqual", "matches", "contains"],
                default_qualification="verifyEqual",
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["timeout"],
                    COMMON_FIELDS["inputAnswers"],
                    FieldDefinition(
                        name="setUpCode",
                        type=FieldType.ARRAY,
                        array_item_type=FieldType.CODE,
                        description="MATLAB/Octave code to run before tests",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["value"],
                    COMMON_FIELDS["qualification"],
                    COMMON_FIELDS["relativeTolerance"],
                    COMMON_FIELDS["absoluteTolerance"],
                    FieldDefinition(
                        name="evalString",
                        type=FieldType.CODE,
                        description="Expression to evaluate for expected value",
                        required=False
                    ),
                ],
                example={
                    "name": "Variable Tests",
                    "type": "variable",
                    "entryPoint": "solution.m",
                    "tests": [
                        {"name": "x", "qualification": "verifyEqual"},
                        {"name": "result", "value": [1, 2, 3]}
                    ]
                }
            ),
            TestTypeBlock(
                id="graphics",
                name="Graphics",
                description="Check plot/figure properties",
                icon="chart",
                category="variable",
                qualifications=["verifyEqual"],
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    FieldDefinition(
                        name="storeGraphicsArtifacts",
                        type=FieldType.BOOLEAN,
                        description="Save figure images",
                        required=False,
                        default=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],  # Graphics property path
                    COMMON_FIELDS["value"],
                    COMMON_FIELDS["relativeTolerance"],
                ],
                example={
                    "name": "Plot Tests",
                    "type": "graphics",
                    "entryPoint": "plot_data.m",
                    "tests": [
                        {"name": "XLim", "value": [0, 10]},
                        {"name": "Title", "value": "Data Plot"}
                    ]
                }
            ),
            TestTypeBlock(
                id="stdout",
                name="Standard Output",
                description="Check command window output",
                icon="terminal",
                category="output",
                qualifications=["matches", "contains", "regexp"],
                default_qualification="contains",
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["inputAnswers"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["value"],
                    COMMON_FIELDS["pattern"],
                    COMMON_FIELDS["qualification"],
                ],
                example={
                    "name": "Output Tests",
                    "type": "stdout",
                    "tests": [
                        {"name": "output", "qualification": "contains", "pattern": "Result:"}
                    ]
                }
            ),
            TestTypeBlock(
                id="exist",
                name="File Exists",
                description="Check if file exists (and optionally not empty)",
                icon="file",
                category="structure",
                qualifications=[],
                collection_fields=[],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["allowEmpty"],
                ],
                example={
                    "name": "File Check",
                    "type": "exist",
                    "tests": [
                        {"name": "solution.m"},
                        {"name": "output.mat", "allowEmpty": True}
                    ]
                }
            ),
            TestTypeBlock(
                id="structural",
                name="Structural",
                description="Check code structure",
                icon="code",
                category="structure",
                qualifications=["count"],
                collection_fields=[
                    FieldDefinition(
                        name="file",
                        type=FieldType.FILE_PATH,
                        description="File to analyze",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["allowedOccuranceRange"],
                ],
                example={
                    "name": "Structure",
                    "type": "structural",
                    "tests": [
                        {"name": "for", "allowedOccuranceRange": [1, 5]},
                        {"name": "eval", "allowedOccuranceRange": [0, 0]}
                    ]
                }
            ),
        ],
        defaults={
            "timeout": 180.0,
            "relativeTolerance": 1e-12,
            "absoluteTolerance": 0.0001,
        }
    )


def _doc_metric_block(
    id: str, name: str, description: str, icon: str,
    value_description: str, example_file: str, example_tests: list,
) -> TestTypeBlock:
    """Factory for document metric test type blocks (count-based)."""
    return TestTypeBlock(
        id=id,
        name=name,
        description=description,
        icon=icon,
        category="metric",
        qualifications=["verifyEqual", "count"],
        default_qualification="verifyEqual",
        collection_fields=[
            FieldDefinition(
                name="file",
                type=FieldType.FILE_PATH,
                description="Document file to analyze",
                required=False
            ),
        ],
        test_fields=[
            COMMON_FIELDS["name"],
            FieldDefinition(
                name="value",
                type=FieldType.INTEGER,
                description=value_description,
                required=False
            ),
            COMMON_FIELDS["allowedOccuranceRange"],
        ],
        example={
            "name": name,
            "type": id,
            "file": example_file,
            "tests": example_tests,
        }
    )


def _doc_average_block(
    id: str, name: str, description: str, icon: str,
    value_description: str, example_file: str, example_value: float,
    example_tolerance: float,
) -> TestTypeBlock:
    """Factory for document average metric blocks (float-based)."""
    return TestTypeBlock(
        id=id,
        name=name,
        description=description,
        icon=icon,
        category="quality",
        qualifications=["verifyEqual"],
        default_qualification="verifyEqual",
        collection_fields=[
            FieldDefinition(
                name="file",
                type=FieldType.FILE_PATH,
                description="Document file to analyze",
                required=False
            ),
        ],
        test_fields=[
            COMMON_FIELDS["name"],
            FieldDefinition(
                name="value",
                type=FieldType.NUMBER,
                description=value_description,
                required=False
            ),
            COMMON_FIELDS["absoluteTolerance"],
        ],
        example={
            "name": name,
            "type": id,
            "file": example_file,
            "tests": [
                {"name": "avg", "value": example_value, "absoluteTolerance": example_tolerance}
            ],
        }
    )


def get_document_blocks() -> LanguageBlocks:
    """Get test blocks for Document/Text testing"""
    return LanguageBlocks(
        id="document",
        name="Document",
        description="Text analysis for any file type - word count, line count, structure analysis, etc.",
        file_extensions=["*"],  # Any file type - document tests work on any text file
        icon="file-text",
        qualifications=[
            COMMON_QUALIFICATIONS["verifyEqual"],
            COMMON_QUALIFICATIONS["contains"],
            COMMON_QUALIFICATIONS["regexp"],
            COMMON_QUALIFICATIONS["count"],
        ],
        test_types=[
            # Metric blocks (count-based)
            _doc_metric_block("wordcount", "Word Count", "Check document word count", "text",
                "Expected word count", "essay.md",
                [{"name": "minimum_words", "allowedOccuranceRange": [500, 0]}, {"name": "exact_count", "value": 1000}]),
            _doc_metric_block("linecount", "Line Count", "Check document line count", "list",
                "Expected line count", "document.txt",
                [{"name": "lines", "allowedOccuranceRange": [10, 100]}]),
            _doc_metric_block("charcount", "Character Count", "Check document character count", "type",
                "Expected character count", "document.txt",
                [{"name": "total", "allowedOccuranceRange": [1000, 5000]}, {"name": "no_spaces", "allowedOccuranceRange": [800, 4000]}]),
            _doc_metric_block("paragraphcount", "Paragraph Count", "Check document paragraph count", "align-left",
                "Expected paragraph count", "essay.md",
                [{"name": "paragraphs", "allowedOccuranceRange": [5, 20]}]),
            _doc_metric_block("sentencecount", "Sentence Count", "Check document sentence count", "message-square",
                "Expected sentence count", "essay.md",
                [{"name": "sentences", "allowedOccuranceRange": [20, 100]}]),
            _doc_metric_block("headingcount", "Heading Count", "Check markdown heading count", "hash",
                "Expected heading count", "report.md",
                [{"name": "headings", "allowedOccuranceRange": [3, 10]}]),
            _doc_metric_block("uniquewords", "Unique Words", "Check unique word count (vocabulary)", "layers",
                "Expected unique word count", "essay.md",
                [{"name": "unique", "allowedOccuranceRange": [200, 0]}]),
            _doc_metric_block("linkcount", "Link Count", "Check markdown link count", "link",
                "Expected link count", "report.md",
                [{"name": "references", "allowedOccuranceRange": [5, 0]}]),
            _doc_metric_block("imagecount", "Image Count", "Check markdown image count", "image",
                "Expected image count", "report.md",
                [{"name": "figures", "allowedOccuranceRange": [2, 10]}]),
            _doc_metric_block("codeblockcount", "Code Block Count", "Check markdown code block count", "code",
                "Expected code block count", "tutorial.md",
                [{"name": "examples", "allowedOccuranceRange": [3, 0]}]),
            _doc_metric_block("listitemcount", "List Item Count", "Check markdown list item count", "list",
                "Expected list item count", "checklist.md",
                [{"name": "items", "allowedOccuranceRange": [5, 20]}]),
            # Average metric blocks (float-based)
            _doc_average_block("avgwordlength", "Average Word Length", "Check average word length", "bar-chart",
                "Expected average word length", "essay.md", 5.5, 0.5),
            _doc_average_block("avgsentencelength", "Average Sentence Length",
                "Check average sentence length (words per sentence)", "bar-chart-2",
                "Expected average sentence length (words)", "essay.md", 15.0, 3.0),
            # Non-metric blocks
            TestTypeBlock(
                id="section",
                name="Section",
                description="Check for required markdown sections/headings",
                icon="bookmark",
                category="structure",
                qualifications=[],
                collection_fields=[
                    FieldDefinition(
                        name="file",
                        type=FieldType.FILE_PATH,
                        description="Markdown file to analyze",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    FieldDefinition(
                        name="value",
                        type=FieldType.INTEGER,
                        description="Required heading level (1-6)",
                        required=False,
                        min_value=1,
                        max_value=6
                    ),
                ],
                example={
                    "name": "Required Sections",
                    "type": "section",
                    "file": "report.md",
                    "tests": [
                        {"name": "Introduction", "value": 2},
                        {"name": "Methodology", "value": 2},
                        {"name": "Results", "value": 2},
                        {"name": "Conclusion", "value": 2}
                    ]
                }
            ),
            TestTypeBlock(
                id="keyword",
                name="Keyword",
                description="Check for keyword presence/frequency",
                icon="search",
                category="content",
                qualifications=["contains", "count"],
                default_qualification="contains",
                collection_fields=[
                    FieldDefinition(
                        name="file",
                        type=FieldType.FILE_PATH,
                        description="Document file to analyze",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    FieldDefinition(
                        name="value",
                        type=FieldType.INTEGER,
                        description="Expected keyword count",
                        required=False
                    ),
                    COMMON_FIELDS["allowedOccuranceRange"],
                    COMMON_FIELDS["ignoreCase"],
                ],
                example={
                    "name": "Keywords",
                    "type": "keyword",
                    "file": "essay.md",
                    "tests": [
                        {"name": "algorithm", "allowedOccuranceRange": [5, 0]},
                        {"name": "conclusion", "ignoreCase": True}
                    ]
                }
            ),
            TestTypeBlock(
                id="pattern",
                name="Pattern",
                description="Check for regex pattern matches",
                icon="regex",
                category="content",
                qualifications=["regexp", "count"],
                default_qualification="regexp",
                collection_fields=[
                    FieldDefinition(
                        name="file",
                        type=FieldType.FILE_PATH,
                        description="Document file to analyze",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["pattern"],
                    FieldDefinition(
                        name="value",
                        type=FieldType.INTEGER,
                        description="Expected match count",
                        required=False
                    ),
                    COMMON_FIELDS["allowedOccuranceRange"],
                    COMMON_FIELDS["ignoreCase"],
                ],
                example={
                    "name": "Patterns",
                    "type": "pattern",
                    "file": "document.md",
                    "tests": [
                        {"name": "email_pattern", "pattern": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"},
                        {"name": "url_pattern", "pattern": "https?://[^\\s]+"}
                    ]
                }
            ),
            TestTypeBlock(
                id="exist",
                name="File Exists",
                description="Check if document file exists (and optionally not empty)",
                icon="file",
                category="structure",
                qualifications=[],
                collection_fields=[
                    FieldDefinition(
                        name="file",
                        type=FieldType.FILE_PATH,
                        description="Directory to check in",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],  # name is the file pattern
                    COMMON_FIELDS["allowEmpty"],
                ],
                example={
                    "name": "File Existence",
                    "type": "exist",
                    "tests": [
                        {"name": "report.md"},
                        {"name": "README.md"},
                        {"name": "notes.txt", "allowEmpty": True}
                    ]
                }
            ),
            TestTypeBlock(
                id="structural",
                name="Structural",
                description="Check document structure (patterns, keywords)",
                icon="code",
                category="structure",
                qualifications=["count", "regexp"],
                collection_fields=[
                    FieldDefinition(
                        name="file",
                        type=FieldType.FILE_PATH,
                        description="Document file to analyze",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["pattern"],
                    COMMON_FIELDS["allowedOccuranceRange"],
                    COMMON_FIELDS["ignoreCase"],
                ],
                example={
                    "name": "Document Structure",
                    "type": "structural",
                    "file": "essay.md",
                    "tests": [
                        {"name": "introduction", "ignoreCase": True},
                        {"name": "TODO", "allowedOccuranceRange": [0, 0]}
                    ]
                }
            ),
        ],
        defaults={
            "timeout": 30.0,
        }
    )


def get_r_blocks() -> LanguageBlocks:
    """Get test blocks for R"""
    return LanguageBlocks(
        id="r",
        name="R",
        description="R programming language",
        file_extensions=[".R", ".r"],
        icon="r",
        qualifications=[
            COMMON_QUALIFICATIONS["verifyEqual"],
            COMMON_QUALIFICATIONS["matches"],
            COMMON_QUALIFICATIONS["contains"],
            COMMON_QUALIFICATIONS["regexp"],
            COMMON_QUALIFICATIONS["count"],
        ],
        test_types=[
            TestTypeBlock(
                id="variable",
                name="Variable",
                description="Check R variable values",
                icon="variable",
                category="variable",
                qualifications=["verifyEqual", "matches", "contains"],
                default_qualification="verifyEqual",
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["timeout"],
                    FieldDefinition(
                        name="setUpCode",
                        type=FieldType.ARRAY,
                        array_item_type=FieldType.CODE,
                        description="R code to run before tests",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["value"],
                    COMMON_FIELDS["qualification"],
                    COMMON_FIELDS["relativeTolerance"],
                    COMMON_FIELDS["absoluteTolerance"],
                    FieldDefinition(
                        name="evalString",
                        type=FieldType.CODE,
                        description="R expression to evaluate",
                        required=False
                    ),
                ],
                example={
                    "name": "Variable Tests",
                    "type": "variable",
                    "entryPoint": "solution.R",
                    "tests": [
                        {"name": "result", "qualification": "verifyEqual"},
                        {"name": "mean_value", "value": 42.5}
                    ]
                }
            ),
            TestTypeBlock(
                id="stdout",
                name="Standard Output",
                description="Check R console output",
                icon="terminal",
                category="output",
                qualifications=["matches", "contains", "regexp"],
                default_qualification="contains",
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["value"],
                    COMMON_FIELDS["pattern"],
                    COMMON_FIELDS["qualification"],
                ],
                example={
                    "name": "Output Tests",
                    "type": "stdout",
                    "tests": [
                        {"name": "print_result", "qualification": "contains", "pattern": "[1]"}
                    ]
                }
            ),
            TestTypeBlock(
                id="exist",
                name="File Exists",
                description="Check if file exists (and optionally not empty)",
                icon="file",
                category="structure",
                qualifications=[],
                collection_fields=[],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["allowEmpty"],
                ],
                example={
                    "name": "File Check",
                    "type": "exist",
                    "tests": [
                        {"name": "solution.R"},
                        {"name": "data.csv", "allowEmpty": True}
                    ]
                }
            ),
            TestTypeBlock(
                id="structural",
                name="Structural",
                description="Check code structure",
                icon="code",
                category="structure",
                qualifications=["count"],
                collection_fields=[
                    FieldDefinition(
                        name="file",
                        type=FieldType.FILE_PATH,
                        description="File to analyze",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["allowedOccuranceRange"],
                ],
                example={
                    "name": "Structure",
                    "type": "structural",
                    "tests": [
                        {"name": "for", "allowedOccuranceRange": [0, 5]},
                        {"name": "function", "allowedOccuranceRange": [1, 10]}
                    ]
                }
            ),
            TestTypeBlock(
                id="error",
                name="Error",
                description="Check for expected errors in R output",
                icon="error",
                category="output",
                qualifications=["regexp", "contains"],
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["inputAnswers"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["pattern"],
                ],
                example={
                    "name": "Error Handling",
                    "type": "error",
                    "entryPoint": "solution.R",
                    "tests": [
                        {"name": "raises_error"},
                        {"name": "specific_error", "pattern": "object .* not found"}
                    ]
                }
            ),
            TestTypeBlock(
                id="warning",
                name="Warning",
                description="Check for expected warnings in R output",
                icon="warning",
                category="output",
                qualifications=["regexp", "contains"],
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["inputAnswers"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["pattern"],
                ],
                example={
                    "name": "Warning Check",
                    "type": "warning",
                    "entryPoint": "solution.R",
                    "tests": [
                        {"name": "coercion_warning", "pattern": "NAs introduced by coercion"}
                    ]
                }
            ),
        ],
        defaults={
            "timeout": 60.0,
            "relativeTolerance": 1e-12,
            "absoluteTolerance": 0.0001,
        }
    )


def get_julia_blocks() -> LanguageBlocks:
    """Get test blocks for Julia"""
    return LanguageBlocks(
        id="julia",
        name="Julia",
        description="Julia programming language",
        file_extensions=[".jl"],
        icon="julia",
        qualifications=[
            COMMON_QUALIFICATIONS["verifyEqual"],
            COMMON_QUALIFICATIONS["matches"],
            COMMON_QUALIFICATIONS["contains"],
            COMMON_QUALIFICATIONS["regexp"],
            COMMON_QUALIFICATIONS["count"],
        ],
        test_types=[
            TestTypeBlock(
                id="variable",
                name="Variable",
                description="Check Julia variable values",
                icon="variable",
                category="variable",
                qualifications=["verifyEqual", "matches", "contains"],
                default_qualification="verifyEqual",
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["timeout"],
                    FieldDefinition(
                        name="setUpCode",
                        type=FieldType.ARRAY,
                        array_item_type=FieldType.CODE,
                        description="Julia code to run before tests",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["value"],
                    COMMON_FIELDS["qualification"],
                    COMMON_FIELDS["relativeTolerance"],
                    COMMON_FIELDS["absoluteTolerance"],
                    FieldDefinition(
                        name="evalString",
                        type=FieldType.CODE,
                        description="Julia expression to evaluate",
                        required=False
                    ),
                ],
                example={
                    "name": "Variable Tests",
                    "type": "variable",
                    "entryPoint": "solution.jl",
                    "tests": [
                        {"name": "result", "qualification": "verifyEqual"},
                        {"name": "mean_value", "value": 42.5}
                    ]
                }
            ),
            TestTypeBlock(
                id="stdout",
                name="Standard Output",
                description="Check Julia console output",
                icon="terminal",
                category="output",
                qualifications=["matches", "contains", "regexp"],
                default_qualification="contains",
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["value"],
                    COMMON_FIELDS["pattern"],
                    COMMON_FIELDS["qualification"],
                ],
                example={
                    "name": "Output Tests",
                    "type": "stdout",
                    "tests": [
                        {"name": "print_result", "qualification": "contains", "pattern": "Result:"}
                    ]
                }
            ),
            TestTypeBlock(
                id="exist",
                name="File Exists",
                description="Check if file exists (and optionally not empty)",
                icon="file",
                category="structure",
                qualifications=[],
                collection_fields=[],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["allowEmpty"],
                ],
                example={
                    "name": "File Check",
                    "type": "exist",
                    "tests": [
                        {"name": "solution.jl"},
                        {"name": "output.txt", "allowEmpty": True}
                    ]
                }
            ),
            TestTypeBlock(
                id="structural",
                name="Structural",
                description="Check code structure",
                icon="code",
                category="structure",
                qualifications=["count"],
                collection_fields=[
                    FieldDefinition(
                        name="file",
                        type=FieldType.FILE_PATH,
                        description="File to analyze",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["allowedOccuranceRange"],
                ],
                example={
                    "name": "Structure",
                    "type": "structural",
                    "tests": [
                        {"name": "for", "allowedOccuranceRange": [0, 5]},
                        {"name": "function", "allowedOccuranceRange": [1, 10]}
                    ]
                }
            ),
            TestTypeBlock(
                id="error",
                name="Error",
                description="Check for expected errors in Julia output",
                icon="error",
                category="output",
                qualifications=["regexp", "contains"],
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["inputAnswers"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["pattern"],
                ],
                example={
                    "name": "Error Handling",
                    "type": "error",
                    "entryPoint": "solution.jl",
                    "tests": [
                        {"name": "raises_error"},
                        {"name": "specific_error", "pattern": "UndefVarError"}
                    ]
                }
            ),
            TestTypeBlock(
                id="warning",
                name="Warning",
                description="Check for expected warnings in Julia output",
                icon="warning",
                category="output",
                qualifications=["regexp", "contains"],
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["inputAnswers"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["pattern"],
                ],
                example={
                    "name": "Warning Check",
                    "type": "warning",
                    "entryPoint": "solution.jl",
                    "tests": [
                        {"name": "deprecation_warning", "pattern": "deprecated"}
                    ]
                }
            ),
        ],
        defaults={
            "timeout": 60.0,
            "relativeTolerance": 1e-12,
            "absoluteTolerance": 0.0001,
        }
    )


def get_fortran_blocks() -> LanguageBlocks:
    """Get test blocks for Fortran"""
    return LanguageBlocks(
        id="fortran",
        name="Fortran",
        description="Fortran programming language",
        file_extensions=[".f", ".f90", ".f95", ".f03", ".f08", ".for"],
        icon="fortran",
        qualifications=[
            COMMON_QUALIFICATIONS["matches"],
            COMMON_QUALIFICATIONS["contains"],
            COMMON_QUALIFICATIONS["startsWith"],
            COMMON_QUALIFICATIONS["endsWith"],
            COMMON_QUALIFICATIONS["regexp"],
            COMMON_QUALIFICATIONS["regexpMultiline"],
            COMMON_QUALIFICATIONS["numericOutput"],
            COMMON_QUALIFICATIONS["lineCount"],
            COMMON_QUALIFICATIONS["matchesLine"],
            COMMON_QUALIFICATIONS["containsLine"],
            COMMON_QUALIFICATIONS["exitCode"],
            COMMON_QUALIFICATIONS["count"],
        ],
        test_types=[
            TestTypeBlock(
                id="stdout",
                name="Standard Output",
                description="Check program stdout",
                icon="terminal",
                category="output",
                qualifications=["matches", "contains", "startsWith", "endsWith", "regexp", "numericOutput", "lineCount", "matchesLine", "containsLine"],
                default_qualification="contains",
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["timeout"],
                    COMMON_FIELDS["inputAnswers"],
                    FieldDefinition(
                        name="compiler",
                        type=FieldType.ENUM,
                        description="Compiler to use",
                        enum_values=["gfortran", "ifort"],
                        required=False,
                        default="gfortran"
                    ),
                    FieldDefinition(
                        name="compilerFlags",
                        type=FieldType.ARRAY,
                        array_item_type=FieldType.STRING,
                        description="Compiler flags",
                        required=False,
                        examples=[["-Wall", "-O2"], ["-std=f2018"]]
                    ),
                    FieldDefinition(
                        name="args",
                        type=FieldType.ARRAY,
                        array_item_type=FieldType.STRING,
                        description="Command line arguments",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["value"],
                    COMMON_FIELDS["pattern"],
                    COMMON_FIELDS["qualification"],
                    COMMON_FIELDS["ignoreCase"],
                    COMMON_FIELDS["trimOutput"],
                    FieldDefinition(
                        name="lineNumber",
                        type=FieldType.INTEGER,
                        description="Line number to check (1-indexed)",
                        required=False,
                        min_value=1
                    ),
                    FieldDefinition(
                        name="numericTolerance",
                        type=FieldType.NUMBER,
                        description="Tolerance for numeric comparison",
                        required=False,
                        default=1e-6
                    ),
                ],
                example={
                    "name": "Output Tests",
                    "type": "stdout",
                    "entryPoint": "main.f90",
                    "inputAnswers": ["5", "3"],
                    "tests": [
                        {"name": "sum", "qualification": "contains", "pattern": "Sum: 8"},
                        {"name": "numeric", "qualification": "numericOutput", "value": 8}
                    ]
                }
            ),
            TestTypeBlock(
                id="stderr",
                name="Standard Error",
                description="Check program stderr",
                icon="error",
                category="output",
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
                example={
                    "name": "Error Output",
                    "type": "stderr",
                    "entryPoint": "program.f90",
                    "tests": [
                        {"name": "error_msg", "qualification": "contains", "pattern": "Error:"}
                    ]
                }
            ),
            TestTypeBlock(
                id="exitcode",
                name="Exit Code",
                description="Check program exit code",
                icon="exit",
                category="output",
                qualifications=["exitCode"],
                default_qualification="exitCode",
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["inputAnswers"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    FieldDefinition(
                        name="expectedExitCode",
                        type=FieldType.INTEGER,
                        description="Expected exit code",
                        required=False,
                        default=0
                    ),
                ],
                example={
                    "name": "Exit Code",
                    "type": "exitcode",
                    "entryPoint": "program.f90",
                    "tests": [
                        {"name": "success", "expectedExitCode": 0},
                        {"name": "error", "expectedExitCode": 1}
                    ]
                }
            ),
            TestTypeBlock(
                id="exist",
                name="File Exists",
                description="Check if file exists (and optionally not empty)",
                icon="file",
                category="structure",
                qualifications=[],
                collection_fields=[],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["allowEmpty"],
                ],
                example={
                    "name": "File Check",
                    "type": "exist",
                    "tests": [
                        {"name": "main.f90"},
                        {"name": "output.dat", "allowEmpty": True}
                    ]
                }
            ),
            TestTypeBlock(
                id="structural",
                name="Structural",
                description="Check code structure",
                icon="code",
                category="structure",
                qualifications=["count"],
                collection_fields=[
                    FieldDefinition(
                        name="file",
                        type=FieldType.FILE_PATH,
                        description="File to analyze",
                        required=False
                    ),
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["allowedOccuranceRange"],
                ],
                example={
                    "name": "Structure",
                    "type": "structural",
                    "tests": [
                        {"name": "do", "allowedOccuranceRange": [0, 5]},
                        {"name": "subroutine", "allowedOccuranceRange": [1, 10]}
                    ]
                }
            ),
            TestTypeBlock(
                id="error",
                name="Error",
                description="Check for expected runtime errors",
                icon="error",
                category="output",
                qualifications=["regexp", "contains"],
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["inputAnswers"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["pattern"],
                ],
                example={
                    "name": "Error Handling",
                    "type": "error",
                    "entryPoint": "main.f90",
                    "tests": [
                        {"name": "runtime_error"},
                        {"name": "specific_error", "pattern": "SIGFPE"}
                    ]
                }
            ),
            TestTypeBlock(
                id="warning",
                name="Warning",
                description="Check for expected compiler/runtime warnings",
                icon="warning",
                category="output",
                qualifications=["regexp", "contains"],
                collection_fields=[
                    COMMON_FIELDS["entryPoint"],
                    COMMON_FIELDS["inputAnswers"],
                ],
                test_fields=[
                    COMMON_FIELDS["name"],
                    COMMON_FIELDS["pattern"],
                ],
                example={
                    "name": "Warning Check",
                    "type": "warning",
                    "entryPoint": "main.f90",
                    "tests": [
                        {"name": "unused_var", "pattern": "unused variable"}
                    ]
                }
            ),
        ],
        defaults={
            "timeout": 30.0,
            "compileTimeout": 30.0,
        }
    )


# =============================================================================
# Registry and Export Functions
# =============================================================================

def get_language_blocks(language: str) -> LanguageBlocks:
    """Get blocks for a specific language"""
    blocks_map = {
        "python": get_python_blocks,
        "py": get_python_blocks,
        "c": get_c_blocks,
        "cpp": get_c_blocks,
        "c++": get_c_blocks,
        "octave": get_octave_blocks,
        "matlab": get_octave_blocks,
        "r": get_r_blocks,
        "julia": get_julia_blocks,
        "jl": get_julia_blocks,
        "fortran": get_fortran_blocks,
        "f90": get_fortran_blocks,
        "f95": get_fortran_blocks,
        "document": get_document_blocks,
        "doc": get_document_blocks,
        "text": get_document_blocks,
        "markdown": get_document_blocks,
        "md": get_document_blocks,
    }

    getter = blocks_map.get(language.lower())
    if getter:
        return getter()
    raise ValueError(f"Unknown language: {language}")


def get_all_blocks() -> BlockRegistry:
    """Get all language blocks as a registry"""
    return BlockRegistry(
        version="1.0",
        languages=[
            get_python_blocks(),
            get_c_blocks(),
            get_octave_blocks(),
            get_r_blocks(),
            get_julia_blocks(),
            get_fortran_blocks(),
            get_document_blocks(),
        ]
    )


def export_json_schema(output_path: str = None) -> str:
    """Export JSON Schema for all blocks"""
    registry = get_all_blocks()
    schema = registry.model_json_schema()

    # Also include individual schemas
    full_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Computor Framework - Test Blocks",
        "description": "Schema for test case blocks across programming languages",
        "definitions": {
            "FieldType": FieldType.model_json_schema() if hasattr(FieldType, 'model_json_schema') else {"enum": [e.value for e in FieldType]},
            "FieldDefinition": FieldDefinition.model_json_schema(),
            "QualificationBlock": QualificationBlock.model_json_schema(),
            "TestTypeBlock": TestTypeBlock.model_json_schema(),
            "LanguageBlocks": LanguageBlocks.model_json_schema(),
            "BlockRegistry": schema,
        },
        **schema
    }

    json_str = json.dumps(full_schema, indent=2)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(json_str)

    return json_str


def export_test_yaml_schema(output_path: str = None) -> str:
    """Export JSON Schema for test.yaml files.

    This generates a schema from the ctcore Pydantic models (ComputorTestSuite)
    that can be used by VSCode/editors to validate and autocomplete test.yaml files.
    """
    from ctcore.models import ComputorTestSuite

    schema = ComputorTestSuite.model_json_schema()
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["title"] = "Computor Framework - test.yaml"
    schema["description"] = "Schema for test.yaml files used by the Computor testing framework"

    json_str = json.dumps(schema, indent=2)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(json_str)

    return json_str


def get_field_visibility_map() -> Dict[str, Dict[str, Dict[str, List[str]]]]:
    """Get a map of which fields are relevant for each (language, test_type, qualification) combo.

    Returns a nested dict: {language_id: {test_type_id: {qualification_id: [field_names]}}}
    This allows the VSCode extension to show/hide fields dynamically based on user selections.

    The map includes:
    - "collection_fields": fields available at the collection level for this test type
    - "test_fields": fields available at the test level for this test type
    - "qualification_fields": extra fields that become relevant when a specific qualification is chosen
    """
    registry = get_all_blocks()
    visibility = {}

    for lang in registry.languages:
        lang_map = {}
        # Build qualification lookup
        qual_lookup = {q.id: q for q in lang.qualifications}

        for tt in lang.test_types:
            tt_map = {
                "collection_fields": [f.name for f in tt.collection_fields],
                "test_fields": [f.name for f in tt.test_fields],
                "qualifications": tt.qualifications,
                "default_qualification": tt.default_qualification,
                "qualification_fields": {},
            }

            # For each supported qualification, determine which extra fields apply
            for qual_id in tt.qualifications:
                qual = qual_lookup.get(qual_id)
                if not qual:
                    continue
                fields = []
                if qual.uses_value:
                    fields.append("value")
                if qual.uses_pattern:
                    fields.append("pattern")
                if qual.uses_tolerance:
                    fields.extend(["relativeTolerance", "absoluteTolerance"])
                if qual.uses_line_number:
                    fields.append("lineNumber")
                if qual.uses_count:
                    fields.append("allowedOccuranceRange")
                for ef in qual.extra_fields:
                    fields.append(ef.name)
                tt_map["qualification_fields"][qual_id] = fields

            lang_map[tt.id] = tt_map

        visibility[lang.id] = lang_map

    return visibility


def export_field_visibility(output_path: str = None) -> str:
    """Export the field visibility map as JSON.

    This is used by the VSCode extension to dynamically show/hide
    form fields based on test type and qualification selections.
    """
    visibility = get_field_visibility_map()
    json_str = json.dumps(visibility, indent=2)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(json_str)

    return json_str


def _python_type_to_ts(annotation, field_name: str = "") -> str:
    """Convert a Python type annotation to a TypeScript type string."""
    origin = getattr(annotation, '__origin__', None)
    args = getattr(annotation, '__args__', ())

    if annotation is type(None):
        return "null"
    if annotation is str:
        return "string"
    if annotation is int:
        return "number"
    if annotation is float:
        return "number"
    if annotation is bool:
        return "boolean"
    if annotation is Any:
        return "any"

    # Handle Optional (Union[X, None])
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _python_type_to_ts(non_none[0], field_name)
        return " | ".join(_python_type_to_ts(a, field_name) for a in non_none)

    # Handle List
    if origin is list:
        if args:
            inner = _python_type_to_ts(args[0], field_name)
            return f"{inner}[]"
        return "any[]"

    # Handle Dict
    if origin is dict:
        if args and len(args) == 2:
            key_type = _python_type_to_ts(args[0], field_name)
            val_type = _python_type_to_ts(args[1], field_name)
            return f"Record<{key_type}, {val_type}>"
        return "Record<string, any>"

    # Handle Literal
    if origin is Literal:
        return " | ".join(f'"{a}"' for a in args)

    # Handle Pydantic models
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation.__name__

    # Handle enums
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation.__name__

    return "any"


def _snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    parts = name.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])


def _generate_ts_enum(enum_cls: type) -> str:
    """Generate TypeScript type union from a Python enum."""
    values = [f'  | "{m.value}"' for m in enum_cls]
    return f"export type {enum_cls.__name__} =\n" + "\n".join(values) + ";\n"


def _generate_ts_interface(model_cls: type, doc: str = "") -> str:
    """Generate a TypeScript interface from a Pydantic model class."""
    lines = []
    if doc:
        lines.append(f"/**\n * {doc}\n */")
    lines.append(f"export interface {model_cls.__name__} {{")

    for name, field_info in model_cls.model_fields.items():
        ts_name = _snake_to_camel(name)
        annotation = field_info.annotation
        ts_type = _python_type_to_ts(annotation, name)
        optional = "?" if not field_info.is_required() else ""
        desc = field_info.description or ""
        if desc:
            lines.append(f"  /** {desc} */")
        lines.append(f"  {ts_name}{optional}: {ts_type};")

    lines.append("}")
    return "\n".join(lines)


def export_typescript(output_path: str = None) -> str:
    """Export TypeScript interfaces, auto-generated from Pydantic models."""
    sections = [
        "// Auto-generated TypeScript interfaces for Computor Framework",
        "// Generated from Pydantic models in blocks/models.py",
        "",
        _generate_ts_enum(FieldType),
        _generate_ts_interface(FieldDefinition, "Definition of a single configuration field"),
        "",
        _generate_ts_interface(QualificationBlock, "Definition of a qualification/comparison type"),
        "",
        _generate_ts_interface(TestTypeBlock, "Definition of a test type"),
        "",
        _generate_ts_interface(LanguageBlocks, "All test blocks available for a programming language"),
        "",
        _generate_ts_interface(BlockRegistry, "Registry of all language blocks"),
    ]

    # Add test.yaml interfaces (these come from ctcore models but are
    # included here for convenience in the VSCode extension)
    sections.extend([
        "",
        "/**",
        " * Individual test case configuration",
        " */",
        "export interface TestCase {",
        "  name: string;",
        "  qualification?: string;",
        "  value?: any;",
        "  pattern?: string;",
        "  expectedExitCode?: number;",
        "  lineNumber?: number;",
        "  ignoreCase?: boolean;",
        "  trimOutput?: boolean;",
        "  relativeTolerance?: number;",
        "  absoluteTolerance?: number;",
        "  numericTolerance?: number;",
        "  allowedOccuranceRange?: [number, number];",
        "  evalString?: string;",
        "  typeCheck?: boolean;",
        "  shapeCheck?: boolean;",
        "  countRequirement?: number;",
        "  allowEmpty?: boolean;",
        "  occuranceType?: string;",
        "}",
        "",
        "/**",
        " * Test collection (group of related tests)",
        " */",
        "export interface TestCollection {",
        "  name: string;",
        "  type: string;",
        "  description?: string;",
        "  entryPoint?: string;",
        "  file?: string;",
        "  timeout?: number;",
        "  inputAnswers?: string[];",
        "  setUpCode?: string[];",
        "  tearDownCode?: string[];",
        "  compiler?: string;",
        "  compilerFlags?: string[];",
        "  linkerFlags?: string[];",
        "  args?: string[];",
        "  storeGraphicsArtifacts?: boolean;",
        "  tests: TestCase[];",
        "}",
        "",
        "/**",
        " * Complete test suite definition",
        " */",
        "export interface TestSuite {",
        "  name?: string;",
        "  description?: string;",
        "  version?: string;",
        "  properties: {",
        "    timeout?: number;",
        "    relativeTolerance?: number;",
        "    absoluteTolerance?: number;",
        "    tests: TestCollection[];",
        "  };",
        "}",
        "",
    ])

    ts_code = "\n".join(sections)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(ts_code)

    return ts_code


# =============================================================================
# YAML Template Generation
# =============================================================================

class TestTemplate(BaseModel):
    """A template for generating test.yaml snippets"""
    name: str = Field(description="Template name")
    description: str = Field(description="What this template tests")
    language: str = Field(description="Target language")
    test_type: str = Field(description="Test type ID")
    yaml_snippet: str = Field(description="YAML snippet to insert")
    placeholders: Dict[str, str] = Field(default={}, description="Placeholders and their descriptions")


class TemplateCategory(BaseModel):
    """Category of templates"""
    id: str
    name: str
    description: str
    templates: List[TestTemplate]


def generate_test_yaml(
    language: str,
    test_type: str,
    test_name: str = "Test",
    collection_name: str = "Test Collection",
    entry_point: str = None,
    qualification: str = None,
    **kwargs
) -> str:
    """Generate a test.yaml snippet for a specific language and test type.

    Args:
        language: Language ID (python, c, octave, r)
        test_type: Test type ID (variable, stdout, etc.)
        test_name: Name for the individual test
        collection_name: Name for the test collection
        entry_point: Entry point file (auto-detected if not provided)
        qualification: Qualification type (uses default if not provided)
        **kwargs: Additional fields to include

    Returns:
        YAML string ready to insert into test.yaml
    """
    import yaml

    lang_blocks = get_language_blocks(language)

    # Find the test type
    test_type_block = None
    for tt in lang_blocks.test_types:
        if tt.id == test_type:
            test_type_block = tt
            break

    if not test_type_block:
        raise ValueError(f"Unknown test type '{test_type}' for language '{language}'")

    # Build collection
    collection: Dict[str, Any] = {
        "name": collection_name,
        "type": test_type,
    }

    # Add entry point if applicable
    if entry_point:
        collection["entryPoint"] = entry_point
    elif any(f.name == "entryPoint" for f in test_type_block.collection_fields):
        # Suggest default entry point based on language
        ext_map = {
            "python": "solution.py",
            "c": "main.c",
            "octave": "solution.m",
            "r": "solution.R",
        }
        collection["entryPoint"] = ext_map.get(language, "main")

    # Add any collection-level kwargs
    collection_field_names = {f.name for f in test_type_block.collection_fields}
    for key, value in kwargs.items():
        if key in collection_field_names and value is not None:
            collection[key] = value

    # Build individual test
    test: Dict[str, Any] = {
        "name": test_name,
    }

    # Add qualification
    if qualification:
        test["qualification"] = qualification
    elif test_type_block.default_qualification:
        test["qualification"] = test_type_block.default_qualification

    # Add test-level kwargs
    test_field_names = {f.name for f in test_type_block.test_fields}
    for key, value in kwargs.items():
        if key in test_field_names and key != "name" and value is not None:
            test[key] = value

    collection["tests"] = [test]

    # Convert to YAML
    return yaml.dump([collection], default_flow_style=False, sort_keys=False, allow_unicode=True)


def generate_full_test_yaml(
    language: str,
    name: str = "Tests",
    description: str = None,
    collections: List[Dict[str, Any]] = None,
    **properties
) -> str:
    """Generate a complete test.yaml file structure.

    Args:
        language: Language ID
        name: Test suite name
        description: Test suite description
        collections: List of test collection configurations
        **properties: Additional properties (timeout, tolerances, etc.)

    Returns:
        Complete test.yaml content
    """
    import yaml

    lang_blocks = get_language_blocks(language)

    # Build properties with defaults
    props: Dict[str, Any] = {}
    props.update(lang_blocks.defaults)
    props.update(properties)

    # Add collections
    if collections:
        props["tests"] = collections
    else:
        props["tests"] = []

    # Build full structure
    result: Dict[str, Any] = {
        "name": name,
    }
    if description:
        result["description"] = description
    result["version"] = "1.0"
    result["properties"] = props

    return yaml.dump(result, default_flow_style=False, sort_keys=False, allow_unicode=True)


# =============================================================================
# Pre-built Templates
# =============================================================================

def get_python_templates() -> List[TestTemplate]:
    """Get pre-built templates for Python"""
    return [
        TestTemplate(
            name="Variable Check",
            description="Check a variable's value after running the script",
            language="python",
            test_type="variable",
            yaml_snippet="""- name: "Variable Tests"
  type: variable
  entryPoint: solution.py
  tests:
    - name: result
      qualification: verifyEqual
      # value: <expected_value>  # Or use evalString for reference comparison
""",
            placeholders={
                "result": "Variable name to check",
                "solution.py": "Entry point file",
            }
        ),
        TestTemplate(
            name="Variable with Tolerance",
            description="Check numeric variable with tolerance",
            language="python",
            test_type="variable",
            yaml_snippet="""- name: "Numeric Tests"
  type: variable
  entryPoint: solution.py
  tests:
    - name: result
      qualification: verifyEqual
      relativeTolerance: 1e-6
      absoluteTolerance: 0.0001
""",
            placeholders={
                "result": "Numeric variable name",
            }
        ),
        TestTemplate(
            name="Standard Output",
            description="Check program prints expected output",
            language="python",
            test_type="stdout",
            yaml_snippet="""- name: "Output Tests"
  type: stdout
  entryPoint: solution.py
  tests:
    - name: contains_hello
      qualification: contains
      pattern: "Hello"
""",
            placeholders={
                "Hello": "Text to search for in output",
            }
        ),
        TestTemplate(
            name="Output with Input",
            description="Check output after providing stdin input",
            language="python",
            test_type="stdout",
            yaml_snippet="""- name: "Interactive Tests"
  type: stdout
  entryPoint: solution.py
  inputAnswers:
    - "input_line_1"
    - "input_line_2"
  tests:
    - name: output_check
      qualification: contains
      pattern: "expected output"
""",
            placeholders={
                "input_line_1": "First line of input",
                "input_line_2": "Second line of input",
                "expected output": "Text to find in output",
            }
        ),
        TestTemplate(
            name="File Exists",
            description="Check that required files exist",
            language="python",
            test_type="exist",
            yaml_snippet="""- name: "File Check"
  type: exist
  tests:
    - name: solution.py
""",
            placeholders={
                "solution.py": "File that must exist",
            }
        ),
        TestTemplate(
            name="Structural - Forbidden Constructs",
            description="Forbid certain keywords or functions",
            language="python",
            test_type="structural",
            yaml_snippet="""- name: "Code Structure"
  type: structural
  tests:
    - name: eval
      allowedOccuranceRange: [0, 0]
    - name: exec
      allowedOccuranceRange: [0, 0]
""",
            placeholders={
                "eval": "Forbidden keyword/function",
            }
        ),
        TestTemplate(
            name="Structural - Required Constructs",
            description="Require certain keywords or functions",
            language="python",
            test_type="structural",
            yaml_snippet="""- name: "Code Structure"
  type: structural
  tests:
    - name: for
      allowedOccuranceRange: [1, 10]
    - name: def
      allowedOccuranceRange: [1, 5]
""",
            placeholders={
                "for": "Required construct",
            }
        ),
        TestTemplate(
            name="Error Expected",
            description="Check that code raises an error",
            language="python",
            test_type="error",
            yaml_snippet="""- name: "Error Handling"
  type: error
  entryPoint: solution.py
  tests:
    - name: raises_error
""",
            placeholders={}
        ),
    ]


def get_c_templates() -> List[TestTemplate]:
    """Get pre-built templates for C/C++"""
    return [
        TestTemplate(
            name="Standard Output",
            description="Check program stdout",
            language="c",
            test_type="stdout",
            yaml_snippet="""- name: "Output Tests"
  type: stdout
  entryPoint: main.c
  tests:
    - name: hello_output
      qualification: contains
      pattern: "Hello"
""",
            placeholders={
                "main.c": "Source file to compile",
                "Hello": "Expected output text",
            }
        ),
        TestTemplate(
            name="Output with Input",
            description="Check output after stdin input",
            language="c",
            test_type="stdout",
            yaml_snippet="""- name: "Interactive Tests"
  type: stdout
  entryPoint: main.c
  inputAnswers:
    - "5"
    - "3"
  tests:
    - name: sum_result
      qualification: contains
      pattern: "Sum: 8"
""",
            placeholders={
                "5": "First input",
                "3": "Second input",
                "Sum: 8": "Expected output",
            }
        ),
        TestTemplate(
            name="Numeric Output",
            description="Extract and verify numeric values",
            language="c",
            test_type="stdout",
            yaml_snippet="""- name: "Numeric Tests"
  type: stdout
  entryPoint: main.c
  tests:
    - name: numeric_check
      qualification: numericOutput
      value: 42
      numericTolerance: 0.001
""",
            placeholders={
                "42": "Expected numeric value",
            }
        ),
        TestTemplate(
            name="Exit Code",
            description="Verify program exit code",
            language="c",
            test_type="exitcode",
            yaml_snippet="""- name: "Exit Code"
  type: exitcode
  entryPoint: main.c
  tests:
    - name: success_exit
      expectedExitCode: 0
""",
            placeholders={
                "0": "Expected exit code",
            }
        ),
        TestTemplate(
            name="Compilation Test",
            description="Test that code compiles successfully",
            language="c",
            test_type="compile",
            yaml_snippet="""- name: "Compilation"
  type: compile
  entryPoint: main.c
  compiler: gcc
  compilerFlags:
    - "-Wall"
    - "-Werror"
  tests:
    - name: compiles
      value: true
""",
            placeholders={
                "main.c": "Source file",
            }
        ),
        TestTemplate(
            name="Structural Analysis",
            description="Check code structure (functions, keywords)",
            language="c",
            test_type="structural",
            yaml_snippet="""- name: "Structure"
  type: structural
  entryPoint: main.c
  tests:
    - name: main
    - name: printf
      allowedOccuranceRange: [1, 10]
    - name: goto
      allowedOccuranceRange: [0, 0]
""",
            placeholders={
                "main": "Function that must exist",
                "goto": "Forbidden keyword",
            }
        ),
        TestTemplate(
            name="Error Output (stderr)",
            description="Check stderr output",
            language="c",
            test_type="stderr",
            yaml_snippet="""- name: "Error Messages"
  type: stderr
  entryPoint: main.c
  tests:
    - name: error_msg
      qualification: contains
      pattern: "Error:"
""",
            placeholders={
                "Error:": "Expected error text",
            }
        ),
    ]


def get_octave_templates() -> List[TestTemplate]:
    """Get pre-built templates for Octave/MATLAB"""
    return [
        TestTemplate(
            name="Variable Check",
            description="Check workspace variable value",
            language="octave",
            test_type="variable",
            yaml_snippet="""- name: "Variable Tests"
  type: variable
  entryPoint: solution.m
  tests:
    - name: result
      qualification: verifyEqual
""",
            placeholders={
                "result": "Variable name",
                "solution.m": "Script file",
            }
        ),
        TestTemplate(
            name="Variable with Tolerance",
            description="Check numeric variable with tolerance",
            language="octave",
            test_type="variable",
            yaml_snippet="""- name: "Numeric Tests"
  type: variable
  entryPoint: solution.m
  tests:
    - name: x
      qualification: verifyEqual
      relativeTolerance: 1e-12
      absoluteTolerance: 0.0001
""",
            placeholders={
                "x": "Numeric variable",
            }
        ),
        TestTemplate(
            name="Matrix Variable",
            description="Check matrix/array value",
            language="octave",
            test_type="variable",
            yaml_snippet="""- name: "Matrix Tests"
  type: variable
  entryPoint: solution.m
  tests:
    - name: A
      qualification: verifyEqual
      value: [[1, 2], [3, 4]]
""",
            placeholders={
                "A": "Matrix variable name",
                "[[1, 2], [3, 4]]": "Expected matrix value",
            }
        ),
        TestTemplate(
            name="Graphics Test",
            description="Check plot/figure properties",
            language="octave",
            test_type="graphics",
            yaml_snippet="""- name: "Plot Tests"
  type: graphics
  entryPoint: plot_data.m
  storeGraphicsArtifacts: true
  tests:
    - name: XLim
      value: [0, 10]
    - name: YLim
      value: [0, 100]
""",
            placeholders={
                "XLim": "Graphics property",
            }
        ),
        TestTemplate(
            name="Standard Output",
            description="Check console output",
            language="octave",
            test_type="stdout",
            yaml_snippet="""- name: "Output Tests"
  type: stdout
  entryPoint: solution.m
  tests:
    - name: output
      qualification: contains
      pattern: "Result:"
""",
            placeholders={
                "Result:": "Text to find in output",
            }
        ),
        TestTemplate(
            name="File Exists",
            description="Check file exists",
            language="octave",
            test_type="exist",
            yaml_snippet="""- name: "File Check"
  type: exist
  tests:
    - name: solution.m
""",
            placeholders={}
        ),
        TestTemplate(
            name="Structural",
            description="Check code structure",
            language="octave",
            test_type="structural",
            yaml_snippet="""- name: "Code Structure"
  type: structural
  tests:
    - name: for
      allowedOccuranceRange: [1, 10]
    - name: eval
      allowedOccuranceRange: [0, 0]
""",
            placeholders={}
        ),
    ]


def get_r_templates() -> List[TestTemplate]:
    """Get pre-built templates for R"""
    return [
        TestTemplate(
            name="Variable Check",
            description="Check R variable value",
            language="r",
            test_type="variable",
            yaml_snippet="""- name: "Variable Tests"
  type: variable
  entryPoint: solution.R
  tests:
    - name: result
      qualification: verifyEqual
""",
            placeholders={
                "result": "Variable name",
            }
        ),
        TestTemplate(
            name="Numeric with Tolerance",
            description="Check numeric variable with tolerance",
            language="r",
            test_type="variable",
            yaml_snippet="""- name: "Numeric Tests"
  type: variable
  entryPoint: solution.R
  tests:
    - name: x
      qualification: verifyEqual
      relativeTolerance: 1e-12
      absoluteTolerance: 0.0001
""",
            placeholders={
                "x": "Numeric variable",
            }
        ),
        TestTemplate(
            name="Vector Variable",
            description="Check vector value",
            language="r",
            test_type="variable",
            yaml_snippet="""- name: "Vector Tests"
  type: variable
  entryPoint: solution.R
  tests:
    - name: vec
      qualification: verifyEqual
      value: [1, 2, 3, 4, 5]
""",
            placeholders={
                "vec": "Vector variable name",
            }
        ),
        TestTemplate(
            name="Standard Output",
            description="Check R console output",
            language="r",
            test_type="stdout",
            yaml_snippet="""- name: "Output Tests"
  type: stdout
  entryPoint: solution.R
  tests:
    - name: print_output
      qualification: contains
      pattern: "[1]"
""",
            placeholders={
                "[1]": "Expected output pattern",
            }
        ),
        TestTemplate(
            name="File Exists",
            description="Check file exists",
            language="r",
            test_type="exist",
            yaml_snippet="""- name: "File Check"
  type: exist
  tests:
    - name: solution.R
""",
            placeholders={}
        ),
        TestTemplate(
            name="Structural",
            description="Check code structure",
            language="r",
            test_type="structural",
            yaml_snippet="""- name: "Code Structure"
  type: structural
  tests:
    - name: function
      allowedOccuranceRange: [1, 10]
    - name: eval
      allowedOccuranceRange: [0, 0]
""",
            placeholders={}
        ),
    ]


def get_julia_templates() -> List[TestTemplate]:
    """Get pre-built templates for Julia"""
    return [
        TestTemplate(
            name="Variable Check",
            description="Check Julia variable value",
            language="julia",
            test_type="variable",
            yaml_snippet="""- name: "Variable Tests"
  type: variable
  entryPoint: solution.jl
  tests:
    - name: result
      qualification: verifyEqual
""",
            placeholders={
                "result": "Variable name",
            }
        ),
        TestTemplate(
            name="Variable with Tolerance",
            description="Check numeric variable with tolerance",
            language="julia",
            test_type="variable",
            yaml_snippet="""- name: "Numeric Tests"
  type: variable
  entryPoint: solution.jl
  tests:
    - name: x
      qualification: verifyEqual
      relativeTolerance: 1e-12
      absoluteTolerance: 0.0001
""",
            placeholders={
                "x": "Numeric variable",
            }
        ),
        TestTemplate(
            name="Standard Output",
            description="Check Julia console output",
            language="julia",
            test_type="stdout",
            yaml_snippet="""- name: "Output Tests"
  type: stdout
  entryPoint: solution.jl
  tests:
    - name: output
      qualification: contains
      pattern: "Hello"
""",
            placeholders={
                "Hello": "Expected output pattern",
            }
        ),
        TestTemplate(
            name="File Exists",
            description="Check file exists",
            language="julia",
            test_type="exist",
            yaml_snippet="""- name: "File Check"
  type: exist
  tests:
    - name: solution.jl
""",
            placeholders={}
        ),
        TestTemplate(
            name="Structural",
            description="Check code structure",
            language="julia",
            test_type="structural",
            yaml_snippet="""- name: "Code Structure"
  type: structural
  tests:
    - name: function
      allowedOccuranceRange: [1, 10]
    - name: eval
      allowedOccuranceRange: [0, 0]
""",
            placeholders={}
        ),
        TestTemplate(
            name="Error Expected",
            description="Check that code raises an error",
            language="julia",
            test_type="error",
            yaml_snippet="""- name: "Error Tests"
  type: error
  entryPoint: solution.jl
  tests:
    - name: error_check
      pattern: "DomainError"
""",
            placeholders={
                "DomainError": "Expected error pattern",
            }
        ),
    ]


def get_fortran_templates() -> List[TestTemplate]:
    """Get pre-built templates for Fortran"""
    return [
        TestTemplate(
            name="Standard Output",
            description="Check program stdout",
            language="fortran",
            test_type="stdout",
            yaml_snippet="""- name: "Output Tests"
  type: stdout
  entryPoint: solution.f90
  tests:
    - name: output
      qualification: contains
      pattern: "Hello"
""",
            placeholders={
                "solution.f90": "Source file",
                "Hello": "Expected output pattern",
            }
        ),
        TestTemplate(
            name="Output with Input",
            description="Check output after providing stdin input",
            language="fortran",
            test_type="stdout",
            yaml_snippet="""- name: "Input/Output Tests"
  type: stdout
  entryPoint: solution.f90
  inputAnswers:
    - "42"
  tests:
    - name: output
      qualification: contains
      pattern: "Result: 42"
""",
            placeholders={
                "solution.f90": "Source file",
                "42": "Input value",
                "Result: 42": "Expected output",
            }
        ),
        TestTemplate(
            name="Numeric Output",
            description="Extract and verify numeric values",
            language="fortran",
            test_type="stdout",
            yaml_snippet="""- name: "Numeric Output"
  type: stdout
  entryPoint: solution.f90
  tests:
    - name: numeric_check
      qualification: numericOutput
      value: 42
      pattern: "Result: (\\d+)"
""",
            placeholders={
                "solution.f90": "Source file",
                "42": "Expected numeric value",
            }
        ),
        TestTemplate(
            name="Exit Code",
            description="Verify program exit code",
            language="fortran",
            test_type="exitcode",
            yaml_snippet="""- name: "Exit Code"
  type: exitcode
  entryPoint: solution.f90
  tests:
    - name: success
      expectedExitCode: 0
""",
            placeholders={
                "solution.f90": "Source file",
            }
        ),
        TestTemplate(
            name="File Exists",
            description="Check file exists",
            language="fortran",
            test_type="exist",
            yaml_snippet="""- name: "File Check"
  type: exist
  tests:
    - name: solution.f90
""",
            placeholders={}
        ),
        TestTemplate(
            name="Structural Analysis",
            description="Check code structure (subroutines, keywords)",
            language="fortran",
            test_type="structural",
            yaml_snippet="""- name: "Code Structure"
  type: structural
  entryPoint: solution.f90
  tests:
    - name: program
    - name: write
      allowedOccuranceRange: [1, 20]
    - name: goto
      allowedOccuranceRange: [0, 0]
""",
            placeholders={}
        ),
    ]


def get_document_templates() -> List[TestTemplate]:
    """Get pre-built templates for Document testing"""
    return [
        TestTemplate(
            name="Word Count",
            description="Check document word count",
            language="document",
            test_type="wordcount",
            yaml_snippet="""- name: "Word Count"
  type: wordcount
  file: essay.md
  tests:
    - name: minimum_words
      allowedOccuranceRange: [500, 0]
""",
            placeholders={
                "essay.md": "Document file to check",
                "500": "Minimum word count",
            }
        ),
        TestTemplate(
            name="Line Count",
            description="Check document line count",
            language="document",
            test_type="linecount",
            yaml_snippet="""- name: "Line Count"
  type: linecount
  file: document.txt
  tests:
    - name: lines
      allowedOccuranceRange: [10, 100]
""",
            placeholders={
                "document.txt": "File to check",
                "10": "Minimum lines",
                "100": "Maximum lines",
            }
        ),
        TestTemplate(
            name="Required Sections",
            description="Check for required markdown sections",
            language="document",
            test_type="section",
            yaml_snippet="""- name: "Required Sections"
  type: section
  file: report.md
  tests:
    - name: Introduction
      value: 2
    - name: Methodology
      value: 2
    - name: Results
      value: 2
    - name: Conclusion
      value: 2
""",
            placeholders={
                "Introduction": "Section heading name",
                "2": "Required heading level (1-6)",
            }
        ),
        TestTemplate(
            name="Keyword Check",
            description="Check for required keywords",
            language="document",
            test_type="keyword",
            yaml_snippet="""- name: "Keywords"
  type: keyword
  file: essay.md
  tests:
    - name: algorithm
      allowedOccuranceRange: [5, 0]
    - name: hypothesis
      ignoreCase: true
""",
            placeholders={
                "algorithm": "Required keyword",
                "5": "Minimum occurrences",
            }
        ),
        TestTemplate(
            name="Forbidden Content",
            description="Check that certain content is NOT present",
            language="document",
            test_type="keyword",
            yaml_snippet="""- name: "Forbidden Content"
  type: keyword
  file: essay.md
  tests:
    - name: TODO
      allowedOccuranceRange: [0, 0]
    - name: FIXME
      allowedOccuranceRange: [0, 0]
""",
            placeholders={
                "TODO": "Forbidden keyword",
            }
        ),
        TestTemplate(
            name="Pattern Match",
            description="Check for regex pattern matches",
            language="document",
            test_type="pattern",
            yaml_snippet="""- name: "Patterns"
  type: pattern
  file: document.md
  tests:
    - name: email_present
      pattern: "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
    - name: url_present
      pattern: "https?://[^\\s]+"
""",
            placeholders={
                "email_present": "Test name",
            }
        ),
        TestTemplate(
            name="File Exists",
            description="Check that required files exist",
            language="document",
            test_type="exist",
            yaml_snippet="""- name: "File Check"
  type: exist
  tests:
    - name: report.md
    - name: README.md
""",
            placeholders={
                "report.md": "Required file",
            }
        ),
        TestTemplate(
            name="Markdown Structure",
            description="Check markdown document structure",
            language="document",
            test_type="headingcount",
            yaml_snippet="""- name: "Document Structure"
  type: headingcount
  file: report.md
  tests:
    - name: headings
      allowedOccuranceRange: [3, 10]
""",
            placeholders={
                "3": "Minimum headings",
                "10": "Maximum headings",
            }
        ),
        TestTemplate(
            name="Quality Metrics",
            description="Check document quality (vocabulary, sentence length)",
            language="document",
            test_type="uniquewords",
            yaml_snippet="""- name: "Vocabulary Check"
  type: uniquewords
  file: essay.md
  tests:
    - name: unique
      allowedOccuranceRange: [200, 0]
""",
            placeholders={
                "200": "Minimum unique words",
            }
        ),
        TestTemplate(
            name="Paragraph Count",
            description="Check number of paragraphs",
            language="document",
            test_type="paragraphcount",
            yaml_snippet="""- name: "Paragraph Count"
  type: paragraphcount
  file: essay.md
  tests:
    - name: paragraphs
      allowedOccuranceRange: [5, 20]
""",
            placeholders={
                "5": "Minimum paragraphs",
                "20": "Maximum paragraphs",
            }
        ),
        TestTemplate(
            name="References/Links",
            description="Check for required references (links)",
            language="document",
            test_type="linkcount",
            yaml_snippet="""- name: "References"
  type: linkcount
  file: report.md
  tests:
    - name: references
      allowedOccuranceRange: [5, 0]
""",
            placeholders={
                "5": "Minimum references/links",
            }
        ),
        TestTemplate(
            name="Code Examples",
            description="Check for code block examples",
            language="document",
            test_type="codeblockcount",
            yaml_snippet="""- name: "Code Examples"
  type: codeblockcount
  file: tutorial.md
  tests:
    - name: examples
      allowedOccuranceRange: [3, 0]
""",
            placeholders={
                "3": "Minimum code blocks",
            }
        ),
    ]


def get_templates(language: str = None) -> List[TestTemplate]:
    """Get all templates, optionally filtered by language"""
    all_templates = []

    template_getters = {
        "python": get_python_templates,
        "c": get_c_templates,
        "octave": get_octave_templates,
        "r": get_r_templates,
        "julia": get_julia_templates,
        "fortran": get_fortran_templates,
        "document": get_document_templates,
    }

    if language:
        lang_lower = language.lower()
        # Handle aliases
        if lang_lower in ("cpp", "c++"):
            lang_lower = "c"
        elif lang_lower == "matlab":
            lang_lower = "octave"
        elif lang_lower == "jl":
            lang_lower = "julia"
        elif lang_lower in ("f", "f90", "f95"):
            lang_lower = "fortran"
        elif lang_lower in ("doc", "text", "markdown", "md"):
            lang_lower = "document"

        getter = template_getters.get(lang_lower)
        if getter:
            return getter()
        raise ValueError(f"Unknown language: {language}")

    # Return all
    for getter in template_getters.values():
        all_templates.extend(getter())

    return all_templates


def get_templates_by_test_type(language: str, test_type: str) -> List[TestTemplate]:
    """Get templates for a specific language and test type"""
    templates = get_templates(language)
    return [t for t in templates if t.test_type == test_type]


def export_templates_json(output_path: str = None) -> str:
    """Export all templates as JSON"""
    templates = get_templates()
    data = {
        "version": "1.0",
        "templates": [t.model_dump(mode="json") for t in templates]
    }

    json_str = json.dumps(data, indent=2)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(json_str)

    return json_str
