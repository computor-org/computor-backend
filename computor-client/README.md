# Computor API Client

Python HTTP client library for the Computor platform API.

## Features

- 🚀 **Auto-generated clients** from Pydantic DTOs
- 🔒 **Type-safe** with full type hints
- ⚡ **Async/await** support via httpx
- 🎯 **CRUD operations** for all endpoints
- 🛡️ **Error handling** with custom exceptions
- 📝 **Well documented** with examples

## Installation

```bash
pip install -e computor-client/
```

**Note**: Requires `computor-types>=0.1.0`

## Quick Start

```python
import asyncio
from computor_client import ComputorClient
from computor_types.organizations import OrganizationCreate

async def main():
    # Initialize client
    async with ComputorClient(base_url="http://localhost:8000") as client:
        # Authenticate
        await client.authenticate(username="admin", password="secret")

        # List organizations
        orgs = await client.organizations.list()

        # Create organization
        new_org = await client.organizations.create(
            OrganizationCreate(
                name="My University",
                gitlab_group_path="my-university",
            )
        )

        # Get by ID
        org = await client.organizations.get(new_org.id)

        # Update
        from computor_types.organizations import OrganizationUpdate
        updated = await client.organizations.update(
            org.id,
            OrganizationUpdate(description="Updated!")
        )

        # Delete
        await client.organizations.delete(org.id)

asyncio.run(main())
```

## Available Endpoint Clients

The `ComputorClient` provides access to all API endpoints:

- `client.accounts` - User accounts
- `client.organizations` - Organizations
- `client.course_families` - Course families
- `client.courses` - Courses
- `client.users` - Users
- `client.groups` - Groups
- `client.roles` - Roles
- `client.profiles` - User profiles
- `client.messages` - Messages
- `client.storage` - File storage
- `client.extensions` - Extensions
- `client.languages` - Programming languages
- `client.execution_backends` - Code execution backends
- `client.examples` - Example repositories
- `client.course_content_kinds` - Course content types
- `client.course_content_deployments` - Content deployments
- ... and more

## CRUD Operations

All endpoint clients inherit from `BaseEndpointClient` and support:

```python
# Create
resource = await client.endpoint.create(CreateDTO(...))

# Get by ID
resource = await client.endpoint.get(resource_id)

# List with optional query parameters
resources = await client.endpoint.list()
resources = await client.endpoint.list(QueryDTO(limit=10))

# Update
updated = await client.endpoint.update(resource_id, UpdateDTO(...))

# Delete
await client.endpoint.delete(resource_id)
```

## Error Handling

The client provides custom exceptions for different error scenarios:

```python
from computor_client import (
    ComputorAPIError,
    ComputorAuthenticationError,
    ComputorAuthorizationError,
    ComputorNotFoundError,
    ComputorValidationError,
    ComputorServerError,
)

try:
    user = await client.users.get("invalid-id")
except ComputorNotFoundError as e:
    print(f"User not found: {e.status_code} - {e.message}")
except ComputorAPIError as e:
    print(f"API error: {e.status_code} - {e.message}")
    print(f"Details: {e.detail}")
```

## Authentication

### Using username/password:

```python
async with ComputorClient(base_url="http://localhost:8000") as client:
    await client.authenticate(username="admin", password="secret")
    # Now all requests will include the auth token
```

### Using existing token:

```python
async with ComputorClient(base_url="http://localhost:8000") as client:
    await client.set_token("your-jwt-token")
    # Now all requests will include this token
```

## Advanced Configuration

```python
client = ComputorClient(
    base_url="http://localhost:8000",
    timeout=60.0,  # Request timeout in seconds
    verify_ssl=True,  # SSL verification
    headers={  # Additional headers
        "X-Custom-Header": "value"
    }
)
```

## Using Individual Clients

You can use endpoint clients independently:

```python
import httpx
from computor_client import OrganizationClient
from computor_types.organizations import OrganizationCreate

async with httpx.AsyncClient(base_url="http://localhost:8000") as http_client:
    org_client = OrganizationClient(http_client)
    orgs = await org_client.list()
```

## Type Safety

All clients use Pydantic DTOs from `computor-types` for full type safety:

```python
from computor_types.users import UserCreate

# Type checkers will validate this
new_user = await client.users.create(
    UserCreate(
        username="john",
        email="john@example.com",
        password="secret123",
    )
)

# new_user is typed as UserGet
print(new_user.id)  # ✅ Type checker knows this exists
print(new_user.password)  # ❌ Type checker error - not in UserGet
```

## Examples

See the `examples/` directory for more comprehensive examples:

- `basic_usage.py` - Basic CRUD operations
- More examples coming soon...

## Development

### Regenerate Clients

Clients are auto-generated from `computor-types` EntityInterface definitions:

```bash
source .venv/bin/activate
python src/computor_backend/scripts/generate_python_clients.py
```

This will regenerate all clients in `src/computor_client/generated/`.

### Package Structure

```
computor-client/
├── src/
│   └── computor_client/
│       ├── __init__.py          # Main exports
│       ├── client.py            # ComputorClient class
│       ├── base.py              # BaseEndpointClient
│       ├── exceptions.py        # Custom exceptions
│       └── generated/           # Auto-generated clients
│           ├── __init__.py
│           ├── organizations.py
│           ├── users.py
│           └── ...
├── examples/                    # Usage examples
├── pyproject.toml              # Package config
└── README.md                   # This file
```

## Dependencies

- `computor-types>=0.1.0` - Pydantic DTOs
- `httpx>=0.27.0` - Async HTTP client
- `pydantic>=2.0` - Data validation

## License

Same as main Computor project
