"""
Computor Testing Core - Shared Models

Language-agnostic data models for testing frameworks.

All models are now sourced from computor-types (the single source of truth).
This module re-exports them and provides local utility functions.
"""

import json
import os
import yaml
from pydantic import BaseModel

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

# Person model (source of truth in computor-types)
# Re-exported as ComputorPerson for backward compatibility
from computor_types.codeability_meta import CodeAbilityPerson as ComputorPerson

# New meta format models (source of truth in computor-types)
from computor_types.codeability_meta import (
    ComputorMaterial,
    ExecutionBackendSettings,
    ExecutionBackend,
    ContentMetadata,
    ComputorMetaProperties as ComputorMetaProperty,  # alias for backward compat
    ComputorMeta,
)

# Report models
from computor_types.testing_report import (
    ComputorReport,
    ComputorReportMain,
    ComputorReportSub,
    ComputorReportSummary,
    ComputorReportProperties,
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
