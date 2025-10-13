# Dependency Guidelines

This document defines the architectural boundaries for the Computor monorepo packages to maintain clean separation of concerns.

## Package Architecture

```
┌─────────────────┐
│  computor-types │  Pure DTOs (Pydantic models)
│  (Pure Data)    │  ✓ Framework-agnostic
└────────┬────────┘  ✓ No business logic
         │
         ├──────────────────────────┐
         │                          │
┌────────▼────────┐        ┌────────▼────────┐
│ computor-client │        │  computor-utils │
│  (HTTP Client)  │        │   (Utilities)   │
└────────┬────────┘        └─────────────────┘
         │
         │
┌────────▼────────┐
│  computor-cli   │
│  (CLI Tool)     │
└─────────────────┘
```

## Allowed Dependencies

### computor-types

**Purpose**: Pure data transfer objects (DTOs) for API contracts

**Allowed**:
- ✅ `pydantic` - Core validation framework
- ✅ `email-validator` - Email field validation
- ✅ `keycove` - Token encryption utilities
- ✅ `text-unidecode` - Text normalization
- ✅ `pydantic-yaml` - YAML serialization
- ✅ `pyyaml` - YAML parsing
- ✅ Standard library (typing, datetime, enum, etc.)

**Forbidden**:
- ❌ `fastapi` - Web framework (types must be framework-agnostic)
- ❌ `starlette` - ASGI framework
- ❌ `sqlalchemy` / `sqlalchemy-utils` - Database ORM
- ❌ `flask` / `django` - Web frameworks
- ❌ `computor_backend` - Backend code (circular dependency)

**Rationale**: Types package should be pure data structures that can be used by any client (Python, TypeScript, etc.) without pulling in web framework dependencies.

---

### computor-client

**Purpose**: HTTP client for communicating with Computor API

**Allowed**:
- ✅ `httpx` - HTTP client library
- ✅ `pydantic` - Data validation
- ✅ `computor-types` - DTO imports
- ✅ Standard library

**Forbidden**:
- ❌ `computor_backend` - Backend code (client should be independent)
- ❌ `fastapi` / `starlette` - Web frameworks
- ❌ `sqlalchemy` - Database ORM
- ❌ Any web framework

**Rationale**: Client should be a thin HTTP wrapper that can work independently of the backend implementation.

---

### computor-cli

**Purpose**: Command-line interface for Computor operations

**Allowed**:
- ✅ `click` - CLI framework
- ✅ `httpx` - HTTP operations
- ✅ `pydantic` - Data validation
- ✅ `pyyaml` - YAML parsing
- ✅ `computor-types` - DTO imports
- ✅ `computor-client` - API client
- ✅ `computor-utils` - Utilities
- ✅ Standard library

**Forbidden**:
- ❌ `computor_backend` - Backend code (should use HTTP client)
- ❌ `fastapi` / `starlette` - Web frameworks
- ❌ `sqlalchemy` - Database ORM
- ❌ Any web framework

**Rationale**: CLI should be a standalone tool that communicates with the backend via HTTP API, not direct imports.

---

### computor-utils

**Purpose**: Shared utilities for deployment mapping, CSV processing, etc.

**Allowed**:
- ✅ `pydantic` - Data validation
- ✅ `pyyaml` - YAML parsing
- ✅ `computor-types` - DTO imports
- ✅ Standard library

**Forbidden**:
- ❌ `computor_backend` - Backend code
- ❌ `fastapi` / `starlette` - Web frameworks
- ❌ `sqlalchemy` - Database ORM
- ❌ Any framework-specific code

**Rationale**: Utils should be generic utilities that don't depend on any specific framework.

---

## Automated Checking

The repository includes an automated checker that runs on every commit via git pre-commit hook.

### Manual Check

```bash
# Check all packages
python scripts/check_forbidden_imports.py

# Check specific package
python scripts/check_forbidden_imports.py --package computor-types
```

### Pre-commit Hook

The git pre-commit hook automatically runs two checks:

1. **Secret Detection** - Prevents committing tokens, passwords, API keys
2. **Forbidden Import Check** - Enforces architectural boundaries

The hook will block commits if violations are found.

### Bypassing Checks (Not Recommended)

```bash
# Skip pre-commit hooks (only in emergency situations)
git commit --no-verify
```

⚠️ **Warning**: Bypassing checks should only be done in exceptional circumstances after careful review.

---

## Common Violations & Fixes

### ❌ Using FastAPI in computor-types

**Problem**:
```python
# computor-types/src/computor_types/my_dto.py
from fastapi import Query  # ❌ Forbidden

class MyDTO(BaseModel):
    ...
```

**Fix**:
```python
# computor-types/src/computor_types/my_dto.py
from pydantic import BaseModel  # ✅ Correct

class MyDTO(BaseModel):
    ...
```

---

### ❌ Importing Backend in CLI

**Problem**:
```python
# computor-cli/src/computor_cli/my_command.py
from computor_backend.model import User  # ❌ Forbidden

def my_command():
    users = db.query(User).all()  # Direct DB access
```

**Fix**:
```python
# computor-cli/src/computor_cli/my_command.py
from computor_cli.auth import get_computor_client  # ✅ Correct
from computor_types.users import UserList

async def my_command():
    client = await get_computor_client(auth)
    users = await client.users.list()  # HTTP API call
```

---

### ❌ Using SQLAlchemy in Types

**Problem**:
```python
# computor-types/src/computor_types/custom_types.py
from sqlalchemy_utils import LtreeType  # ❌ Forbidden
```

**Fix**:
```python
# computor-types/src/computor_types/custom_types.py
from pydantic import GetCoreSchemaHandler  # ✅ Correct
from pydantic_core import core_schema

class Ltree(str):  # Pure Pydantic implementation
    @classmethod
    def __get_pydantic_core_schema__(...):
        ...
```

---

## Adding New Dependencies

When adding a new dependency to any package:

1. **Check if it's allowed** per the guidelines above
2. **Add to `pyproject.toml`** in the appropriate package
3. **Run the checker** to verify: `python scripts/check_forbidden_imports.py`
4. **Update this document** if adding new allowed/forbidden dependencies

---

## Questions?

If you're unsure whether a dependency is appropriate:

1. Check if it violates the architectural boundaries
2. Consider if the functionality could be in a different package
3. Ask: "Does this create a circular dependency or framework coupling?"
4. Consult with the team lead

---

**Last Updated**: 2025-10-13
