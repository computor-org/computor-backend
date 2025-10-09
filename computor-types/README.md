# Computor Types

Pure Pydantic DTOs for the Computor platform.

## Installation

```bash
pip install computor-types
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
# Clone repository
git clone https://github.com/computor/computor-types.git
cd computor-types

# Install in editable mode
pip install -e .[dev]

# Run tests
pytest

# Type checking
mypy src/computor_types
```

## License

MIT
