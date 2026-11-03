# Computor Types

Pure Pydantic DTOs for the Computor platform.

## Installation

The package is not published on PyPI; install it from the monorepo root:

```bash
pip install -e computor-types/
```

## Usage

```python
from computor_types.organizations import OrganizationGet, OrganizationCreate
from computor_types.courses import CourseGet, CourseCreate
from computor_types.users import UserGet, UserCreate

# Use DTOs for type-safe data validation
org = OrganizationGet(
    id="org-123",
    path="university.cs",
    title="Computer Science Department",
    organization_type="organization"
)
```

## What's Included

This package contains all Pydantic DTOs used across the Computor platform:

- **Organizations**: Organization hierarchy management
- **Courses**: Course and course family definitions
- **Users**: User accounts and profiles
- **Submissions**: Student submission models
- **Results**: Test result models
- **Messages**: Messaging and comments
- **Auth**: Authentication models
- **Deployments**: Deployment configuration
- And many more...

## Development

```bash
git clone https://github.com/computor-org/computor-backend.git
cd computor-backend/computor-types

# Install in editable mode
pip install -e .[dev]

# Type checking
mypy src/computor_types
```

## License

MIT
