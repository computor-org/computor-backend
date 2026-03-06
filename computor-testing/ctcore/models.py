"""
Computor Testing Core - Shared Models

Language-agnostic data models for testing frameworks.

Test specification models, enums, report models, and utilities are now
sourced from computor-types (the single source of truth). This module
re-exports them and adds meta.yaml models + local utility functions.
"""

import json
import os
import yaml
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

# =============================================================================
# Re-exports from computor-types (source of truth)
# =============================================================================

# Enums
from computor_types.testing import (
    QualificationEnum,
    TypeEnum,
    StatusEnum,
    ResultEnum,
)

# Base classes
from computor_types.testing import (
    ComputorBase,
    ComputorTestCommon,
    ComputorTestCollectionCommon,
)

# Test specification models
from computor_types.testing import (
    ComputorTest,
    ComputorTestCollection,
    ComputorTestProperty,
    ComputorTestSuite,
    ComputorSpecification,
)

# Constants and utilities
from computor_types.testing import (
    DEFAULTS,
    DIRECTORIES,
    empty_list_to_none,
    empty_string_to_none,
)

# VERSION_REGEX from codeability_meta (the canonical source)
from computor_types.codeability_meta import VERSION_REGEX

# Report models
from computor_types.testing_report import (
    ComputorReport,
    ComputorReportMain,
    ComputorReportSub,
    ComputorReportSummary,
    ComputorReportProperties,
)

# =============================================================================
# Meta.yaml models (local — will be migrated to computor-types in Phase 3)
# =============================================================================


class ComputorMaterial(ComputorBase):
    """
    Reference material link.

    Used for courseMaterials (lecture content) and supportingMaterials (API docs).
    """
    name: str = Field(
        min_length=1,
        description="Identifier/key for this material (e.g., 'mat2str', 'wiki-ASCII')"
    )
    url: str = Field(
        min_length=1,
        description="URL to the resource"
    )


class ComputorPerson(ComputorBase):
    name: Optional[str] = Field(min_length=1, default=None)
    email: Optional[str] = Field(min_length=1, default=None)
    affiliation: Optional[str] = Field(min_length=1, default=None)


class ExecutionBackendSettings(BaseModel):
    """Settings for execution backend - configurable limits and options.

    These settings can be specified in meta.yaml to override defaults.
    The hierarchy is: test.yaml > meta.yaml > tester default
    """
    model_config = ConfigDict(extra="allow")  # Allow language-specific settings

    # Timeout settings
    timeout: Optional[float] = Field(
        default=None, ge=0,
        description="Execution timeout in seconds (overrides test.yaml default)"
    )
    compileTimeout: Optional[float] = Field(
        default=None, ge=0,
        description="Compilation timeout in seconds (for compiled languages)"
    )

    # Resource limits
    memoryLimitMB: Optional[int] = Field(
        default=None, ge=0,
        description="Memory limit in megabytes"
    )
    cpuLimit: Optional[int] = Field(
        default=None, ge=0,
        description="CPU time limit in seconds"
    )
    maxProcesses: Optional[int] = Field(
        default=None, ge=1,
        description="Maximum number of processes/threads"
    )

    # Environment
    env: Optional[List[str]] = Field(
        default=[],
        description="Environment variables (KEY=VALUE format)"
    )

    # Language-specific settings (examples - extra="allow" permits more)
    compiler: Optional[str] = Field(
        default=None,
        description="Compiler to use (gcc, g++, clang, gfortran, etc.)"
    )
    flags: Optional[List[str]] = Field(
        default=None,
        description="Compiler/interpreter flags"
    )


class ExecutionBackend(ComputorBase):
    """Execution backend configuration for meta.yaml.

    Example in meta.yaml:
        properties:
          executionBackend:
            slug: itpcp.exec.c
            version: "13"
            settings:
              timeout: 60
              memoryLimitMB: 256
              compiler: gcc
              flags: ["-Wall", "-Wextra"]
    """
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(
        min_length=1,
        description="Backend identifier (e.g., 'itpcp.exec.mat', 'itpcp.exec.c')"
    )
    version: Optional[str] = Field(
        default=None,
        description="Backend/language version requirement"
    )
    settings: Optional[ExecutionBackendSettings] = Field(
        default=None,
        description="Backend-specific settings (timeout, memory, etc.)"
    )


class ContentMetadata(ComputorBase):
    """
    Content categorization for examples.

    Provides structured metadata for organizing, searching, and filtering examples.
    """
    types: Optional[List[str]] = Field(
        default=[],
        description="Type of example: programming, mathematics, visualization, etc."
    )
    disciplines: Optional[List[str]] = Field(
        default=[],
        description="Curricular classification: mathematics, computer_science, physics, etc."
    )
    topics: Optional[List[str]] = Field(
        default=[],
        description="Hierarchical topics in Ltree format (e.g., 'math.linear_equations', 'prog.loops')"
    )
    tools: Optional[List[str]] = Field(
        default=[],
        description="Tools/languages used: matlab, octave, python, latex, etc."
    )
    tags: Optional[List[str]] = Field(
        default=[],
        description="Free-form tags for additional categorization (replaces keywords)"
    )


class ComputorMetaProperty(ComputorBase):
    """Properties section of meta.yaml"""
    model_config = ConfigDict(extra="forbid")

    studentSubmissionFiles: Optional[List[str]] = Field(default=[])
    additionalFiles: Optional[List[str]] = Field(default=[])
    testFiles: Optional[List[str]] = Field(default=[])
    studentTemplates: Optional[List[str]] = Field(default=[])
    executionBackend: Optional[ExecutionBackend] = Field(
        default=None,
        description="Execution backend configuration"
    )
    testDependencies: Optional[List[str]] = Field(default=[])


class ComputorMeta(ComputorBase):
    """
    Meta.yaml schema for example/assignment metadata (new format).

    This is the proposed new format with 'identifier' instead of 'slug'.
    The old format (CodeAbilityMeta) remains the source of truth in
    computor_types.codeability_meta.

    Removed fields (no longer in use):
    - slug: Renamed to 'identifier'
    - type: No longer in use
    - kind: No longer in use
    - language: Now derived from content/index_*.md files
    - links: Renamed to 'courseMaterials'
    - keywords: Replaced by 'content.tags'
    - testDependencies (root level): Use properties.testDependencies instead
    - executionBackendSlug: Use properties.executionBackend.slug instead
    """
    identifier: Optional[str] = Field(
        default=None,
        min_length=1,
        pattern=r"^[a-z0-9._-]+$",
        description="Unique identifier for this example (e.g., 'itpcp.pgph.mat.hello_world')"
    )
    version: Optional[str] = Field(
        pattern=VERSION_REGEX, default=DEFAULTS["meta"]["version"]
    )
    title: Optional[str] = Field(min_length=1, default=DEFAULTS["meta"]["title"])
    description: Optional[str] = Field(
        min_length=1, default=DEFAULTS["meta"]["description"]
    )
    license: Optional[str] = Field(min_length=1, default=DEFAULTS["meta"]["license"])
    authors: Optional[List[ComputorPerson]] = Field(default=[])
    maintainers: Optional[List[ComputorPerson]] = Field(default=[])
    courseMaterials: Optional[List[ComputorMaterial]] = Field(
        default=[],
        description="Lecture/course materials (presentations, tutorials, etc.)"
    )
    supportingMaterials: Optional[List[ComputorMaterial]] = Field(
        default=[],
        description="API references and documentation (function docs, etc.)"
    )
    content: Optional[ContentMetadata] = Field(
        default=ContentMetadata(),
        description="Content categorization (types, disciplines, topics, tools, tags)"
    )
    properties: Optional[ComputorMetaProperty] = Field(
        default=ComputorMetaProperty()
    )


# =============================================================================
# Utility functions (local to computor-testing)
# =============================================================================


def load_config(classname: BaseModel, path):
    """Load configuration from YAML file"""
    with open(path, "r") as file:
        config = yaml.safe_load(file)
        return classname(**config)


def read_ca_file(classname, path: str):
    """Read Computor configuration file"""
    return load_config(classname, path)


def get_schema(classname: BaseModel):
    """Generate and save JSON schema for a model"""
    schema = classname.model_json_schema()
    pretty = json.dumps(schema, indent=2)
    dir = os.path.abspath(os.path.dirname(__file__))
    name = f"{classname.__name__}_schema.json"
    schemafile = os.path.join(dir, "output", name)
    os.makedirs(os.path.dirname(schemafile), exist_ok=True)
    with open(schemafile, "w") as file:
        file.write(pretty)
    print(pretty)


if __name__ == "__main__":
    get_schema(ComputorSpecification)
    get_schema(ComputorTestSuite)
    get_schema(ComputorMeta)
    get_schema(ComputorReport)
