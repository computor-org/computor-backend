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
    async with ComputorClient(
        base_url="http://localhost:8000",
        api_token="ct_...",
    ) as client:
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

The API supports two schemes, and there is deliberately **no username/password
option** — it exposes no local credential-exchange endpoint.

### API token (services, automation, agents)

```python
async with ComputorClient(
    base_url="http://localhost:8000",
    api_token="ct_...",          # sent as the X-API-Token header
) as client:
    ...
```

### SSO bearer token

Obtained from the Keycloak browser flow. Pair it with a refresh token to get
automatic renewal when a request comes back 401.

```python
client = ComputorClient(
    base_url="http://localhost:8000",
    access_token="your-access-token",
    refresh_token="your-refresh-token",
)

client.access_token                    # read it back, e.g. for a WebSocket handshake
await client.refresh_access_token()    # force a refresh
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

Method names are derived from the route itself, so they are the same shape
everywhere: `list`/`list_<subject>` for array responses, `get`/`get_<subject>`
otherwise, and `create` / `update` / `replace` / `delete` for the rest.

- `get(id)` - Get a single resource by ID
- `list(skip, limit, query)` - List resources, returning the rows
- `list_page(skip, limit, query)` - Same request, returning a `Page`
- `create(data)` - Create a new resource
- `update(id, data)` - Update an existing resource
- `delete(id)` - Delete a resource

### Pagination

List endpoints report the total row count in the `X-Total-Count` header rather
than in the body. `list()` returns just the rows; use `list_page()` when you
need to know whether more remain:

```python
page = await client.courses.list_page(skip=0, limit=50)
print(len(page), "of", page.total)

while page.has_more:
    page = await client.courses.list_page(skip=page.next_skip, limit=50)
```

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
