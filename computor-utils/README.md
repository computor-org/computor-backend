# Computor Utils

Shared utility functions for the Computor platform.

## Overview

This package contains utility functions that are used across multiple Computor packages (backend, CLI, etc.).

## Contents

### 1. VSIX Utilities (`vsix_utils.py`)

Functions for parsing and working with VS Code extension packages (VSIX files).

```python
from computor_utils.vsix_utils import parse_vsix_metadata

# Parse VSIX metadata
with open('extension.vsix', 'rb') as f:
    metadata = parse_vsix_metadata(f.read())
    print(f"Extension: {metadata.publisher}.{metadata.name}@{metadata.version}")
```

### 2. Deployment Mapping (`deployment_mapping/`)

Generic table-to-deployment mapping utilities for converting CSV/table data into deployment configurations.

**Features:**
- ✅ Map arbitrary CSV columns to `UserDeployment`, `AccountDeployment`, `CourseMemberDeployment`
- ✅ JSON-based mapping configuration
- ✅ Template substitution and field transformations
- ✅ Support for multiple course memberships per user
- ✅ Conditional field creation
- ✅ Default values and validation

**Quick Example:**

```python
from computor_utils.deployment_mapping import DeploymentMapper

# Create mapping configuration (JSON)
mapping_config = {
    "version": "1.0",
    "user_fields": {
        "given_name": "First Name",
        "family_name": "Last Name",
        "email": "Email",
        "username": {
            "source": {"template": "{email}"},
            "transform": "extract_username"
        }
    },
    "account_fields": {
        "provider": "gitlab",
        "type": "oauth",
        "gitlab_email": {"source": {"ref": "email"}}
    },
    "course_member_fields": {
        "organization": "kit",
        "course_family": "prog",
        "course": "prog1",
        "role": "_student",
        "group": "Group"
    }
}

# Map CSV to deployment
mapper = DeploymentMapper(mapping_config)
deployment = mapper.map_csv_to_deployments("students.csv")

# Export to YAML
deployment.write_deployment("users_deployment.yaml")
```

**Full Documentation:** [deployment_mapping/README.md](src/computor_utils/deployment_mapping/README.md)

## Installation

```bash
pip install -e .
```

## Development

Install with dev dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

## Documentation

- [Deployment Mapping Guide](src/computor_utils/deployment_mapping/README.md)
- [Project Guidelines](../docs/guideline.md)
