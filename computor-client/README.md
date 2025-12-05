# Computor Client

A type-safe async HTTP client library for the Computor platform.

## Features

- **Async/await support** - Built on httpx for modern async Python
- **Type-safe** - Full type hints and Pydantic model integration
- **Auto-generated clients** - Endpoint clients generated from API definitions
- **Authentication** - Built-in support for username/password and token authentication
- **Automatic token refresh** - Seamless handling of expired tokens
- **Comprehensive exceptions** - Detailed error handling with HTTP status mapping

## Installation

```bash
pip install computor-client
```

Or install with development dependencies:

```bash
pip install computor-client[dev]
```

## Quick Start

```python
from computor_client import ComputorClient

async def main():
    async with ComputorClient(base_url="http://localhost:8000") as client:
        # Authenticate
        await client.login(username="admin", password="secret")

        # List resources
        organizations = await client.organizations.list()

        # Get a single resource
        user = await client.users.get("user-id")

        # Create a resource
        from computor_types.organizations import OrganizationCreate
        new_org = await client.organizations.create(OrganizationCreate(
            title="My Organization",
            path="my_org",
            organization_type="organization",
        ))

        # Update a resource
        from computor_types.organizations import OrganizationUpdate
        updated = await client.organizations.update(
            "org-id",
            OrganizationUpdate(title="Updated Title"),
        )

        # Delete a resource
        await client.organizations.delete("org-id")

# Run with asyncio
import asyncio
asyncio.run(main())
```

## Authentication

### Username/Password Login

```python
async with ComputorClient(base_url="http://localhost:8000") as client:
    await client.login(username="user", password="pass")
    # Client is now authenticated
```

### Pre-existing Tokens

```python
client = ComputorClient(
    base_url="http://localhost:8000",
    access_token="your-access-token",
    refresh_token="your-refresh-token",
)
```

### Manual Token Management

```python
client.set_token("new-access-token", "new-refresh-token")
client.clear_tokens()
```

## Available Endpoint Clients

After authentication, access endpoint clients as attributes:

```python
client.organizations  # OrganizationClient
client.users          # UserClient
client.courses        # CourseClient
client.course_families # CourseFamilyClient
# ... and more
```

Each client provides standard CRUD operations:

- `get(id)` - Get a single resource by ID
- `list(skip, limit, query)` - List resources with pagination
- `create(data)` - Create a new resource
- `update(id, data)` - Update an existing resource
- `delete(id)` - Delete a resource
- `exists(id)` - Check if a resource exists
- `get_all(query)` - Get all matching resources (handles pagination)

## Exception Handling

The library provides detailed exceptions for different error types:

```python
from computor_client import (
    ComputorClientError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    ServerError,
    NetworkError,
)

try:
    user = await client.users.get("nonexistent")
except NotFoundError as e:
    print(f"User not found: {e.message}")
    print(f"Error code: {e.error_code}")
except AuthenticationError as e:
    print(f"Auth failed: {e.message}")
except ComputorClientError as e:
    print(f"API error: {e.message} (HTTP {e.status_code})")
```

## Custom Requests

For endpoints not covered by generated clients:

```python
# GET request
data = await client.get("/custom/endpoint", params={"key": "value"})

# POST request
result = await client.post("/custom/endpoint", json_data={"field": "value"})

# With response model
from pydantic import BaseModel

class CustomResponse(BaseModel):
    id: str
    name: str

response = await client.get("/custom/endpoint", response_model=CustomResponse)
```

## Configuration Options

```python
client = ComputorClient(
    base_url="http://localhost:8000",
    timeout=60.0,              # Request timeout in seconds
    max_retries=5,             # Maximum retry attempts
    headers={"X-Custom": "value"},  # Additional headers
)
```

## Generating Endpoint Clients

Endpoint clients are auto-generated from the API definitions:

```bash
bash generate.sh python-client
```

This generates typed clients in `computor-client/src/computor_client/endpoints/`.

## Development

### Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Type Checking

```bash
mypy src/computor_client
```

## License

MIT License - see LICENSE file for details.
