# Computor CLI

Command-line interface for the Computor platform.

## Features

- 🔐 **Authentication** - Login with basic auth or GitLab SSO
- 📊 **CRUD Operations** - Create, read, update, delete entities
- 🔧 **Administration** - User and system administration
- 👷 **Workers** - Temporal worker management
- 🎨 **Code Generation** - TypeScript/Python client generation
- 📦 **Templates** - Course template management
- 🚀 **Deployment** - Course content deployment

## Installation

```bash
pip install -e computor-cli/
```

**Dependencies**:
- `computor-types>=0.1.0`
- `computor-client>=0.1.0`

## Quick Start

### Login

```bash
# Basic authentication
computor login --auth-method basic --base-url http://localhost:8000

# GitLab SSO
computor login --auth-method gitlab --base-url http://localhost:8000
```

### CRUD Operations

```bash
# List organizations
computor rest list --table organizations

# Create a user
computor rest create --table users

# Get specific entity
computor rest get --table courses --id <course-id>

# Update entity
computor rest update --table organizations --id <org-id>

# Delete entity
computor rest delete --table users --id <user-id>
```

### Worker Management

```bash
# Start Temporal worker
computor worker start

# Start with specific queue
computor worker start --queues computor-tasks

# Check worker status
computor worker status
```

### Code Generation

```bash
# Generate TypeScript interfaces
computor generate-types

# Generate TypeScript API clients
computor generate-clients

# Generate OpenAPI schema
computor generate-schema

# Watch mode for automatic regeneration
computor generate-types --watch
```

### Administration

```bash
# Admin commands
computor admin <subcommand>
```

### Templates

```bash
# Template management
computor templates <subcommand>
```

### Deployment

```bash
# Deploy course content
computor deployment <subcommand>
```

## Available Commands

### Authentication
- `computor login` - Authenticate with API
- `computor logout` - Log out and remove active profile
- `computor status` - Show currently active profile

### CRUD
- `computor rest list` - List entities
- `computor rest get` - Get entity by ID
- `computor rest create` - Create new entity
- `computor rest update` - Update entity
- `computor rest delete` - Delete entity

Available entity types:
- organizations
- course-families
- courses
- course-contents
- course-content-types
- course-groups
- course-members
- course-roles
- users
- results

### Workers
- `computor worker start` - Start Temporal worker
- `computor worker status` - Check worker status
- `computor worker stop` - Stop worker

### Generators
- `computor generate-types` - Generate TypeScript interfaces
- `computor generate-clients` - Generate TypeScript API clients
- `computor generate-schema` - Generate OpenAPI schema
- `computor generate-validators` - Generate validators

### Administration
- `computor admin` - Administrative commands (see `computor admin --help`)

### Templates
- `computor templates` - Template management (see `computor templates --help`)

### Deployment
- `computor deployment` - Deployment operations (see `computor deployment --help`)

### Testing
- `computor test` - Run tests

## Configuration

The CLI stores the active profile in `~/.computor/active_profile.yaml`.

### Profile Structure

```yaml
api_url: http://localhost:8000
basic:
  username: admin
  password: secret
```

Or for GitLab auth:

```yaml
api_url: http://localhost:8000
gitlab:
  url: https://gitlab.com
  token: glpat-xxxxxxxxxxxx
```

## Development

### Package Structure

```
computor-cli/
├── src/
│   └── computor_cli/
│       ├── __init__.py
│       ├── cli.py              # Main CLI entry point
│       ├── auth.py             # Authentication
│       ├── config.py           # Configuration models
│       ├── crud.py             # CRUD operations
│       ├── admin.py            # Admin commands
│       ├── worker.py           # Worker management
│       ├── generate_types.py   # TypeScript generation
│       ├── generate_clients.py # Client generation
│       ├── generate_schema.py  # Schema generation
│       ├── template.py         # Template management
│       ├── deployment.py       # Deployment commands
│       ├── test.py             # Testing commands
│       └── ...
├── pyproject.toml             # Package config
└── README.md                  # This file
```

### Adding New Commands

1. Create a new file in `src/computor_cli/` (e.g., `my_command.py`)
2. Define a click command:

```python
import click

@click.command()
@click.option('--option', '-o', help='Description')
def my_command(option):
    """My custom command."""
    click.echo(f"Running with option: {option}")
```

3. Import and register in `cli.py`:

```python
from .my_command import my_command

# ...

cli.add_command(my_command, "my-command")
```

### Using Computor Client

For new commands, use the `computor-client` package:

```python
import asyncio
import click
from computor_cli.auth import authenticate, get_computor_client
from computor_cli.config import CLIAuthConfig

@click.command()
@authenticate
def my_command(auth: CLIAuthConfig):
    """Example command using computor-client."""

    async def run():
        async with await get_computor_client(auth) as client:
            # Use the client
            orgs = await client.organizations.list()
            for org in orgs:
                click.echo(f"Organization: {org.name}")

    asyncio.run(run())
```

## Migration Notes

This package is part of the Computor platform refactoring:

### Phase 3 Status
- ✅ Package structure created
- ✅ CLI files migrated from `computor_backend.cli`
- ✅ Imports updated to use `computor_types`
- ✅ New `get_computor_client()` function added
- ⚠️ Legacy `get_crud_client()` kept for backward compatibility
- ⚠️ Some commands still use backend directly (will be updated in Phase 4)

### Legacy Compatibility

Some commands still reference `computor_backend` directly:
- Generator commands (generate-types, generate-clients, generate-schema)
- Template commands
- Deployment commands
- Worker commands

These will be fully migrated in Phase 4 when the backend is renamed to `computor_backend`.

## Dependencies

- `click>=8.0` - CLI framework
- `computor-types>=0.1.0` - Pydantic DTOs
- `computor-client>=0.1.0` - API client library
- `httpx>=0.27.0` - HTTP client
- `pydantic>=2.0` - Data validation
- `pyyaml` - Configuration files

## License

Same as main Computor project.
