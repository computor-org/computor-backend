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

- [Project Guidelines](../docs/guideline.md)
