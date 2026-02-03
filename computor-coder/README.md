# Computor Coder

Coder workspace management plugin for the Computor platform.

## Overview

This package provides:
- **Python Plugin** (`src/computor_coder/`) - FastAPI integration for workspace management
- **Deployment Scripts** (`deployment/`) - Docker-based Coder server deployment

## Package Structure

```
computor-coder/
├── pyproject.toml                 # Python package configuration
├── README.md                      # This file
│
├── src/computor_coder/            # Python package
│   ├── __init__.py                # Package exports
│   ├── client.py                  # CoderClient - async HTTP client
│   ├── config.py                  # CoderSettings (pydantic-settings)
│   ├── exceptions.py              # Custom exceptions
│   ├── plugin.py                  # CoderPlugin interface
│   ├── router.py                  # FastAPI API router
│   ├── schemas.py                 # Pydantic DTOs
│   ├── web.py                     # Web interface router
│   ├── py.typed                   # PEP 561 type marker
│   ├── templates/                 # Jinja2 HTML templates
│   └── static/                    # CSS and JavaScript
│
└── deployment/                    # Coder server deployment
    ├── install.sh                 # Main installation script
    ├── stop.sh                    # Stop/cleanup script
    ├── setup-admin.sh             # Admin user creation
    ├── create-user.sh             # Create users via API
    ├── docker-compose.yml         # Docker Compose configuration
    ├── blocked.conf               # Nginx 403 response config
    ├── nginx-coder.conf           # Standalone nginx config
    └── templates/                 # Workspace templates
        ├── python3.13/            # Python 3.13 (Dockerfile + main.tf)
        └── matlab/                # MATLAB (Dockerfile + main.tf)
```

## Installation

### Python Package

```bash
# From computor-fullstack directory
pip install -e computor-coder/
```

### Coder Server

```bash
cd computor-coder/deployment

# Basic installation
./install.sh -D coder.example.com -P 8446

# With admin user
./install.sh -D coder.example.com -P 8446 \
  -u admin -e admin@example.com -w secretpass
```

## Quick Start

### 1. Environment Variables

```bash
CODER_URL=https://coder.example.com
CODER_ADMIN_EMAIL=admin@example.com
CODER_ADMIN_PASSWORD=your-password
CODER_ADMIN_API_SECRET=<from-install.sh>
CODER_ENABLED=true
```

### 2. Basic Usage

```python
from computor_coder import CoderClient, WorkspaceTemplate

async with CoderClient() as client:
    # Provision workspace for a user
    result = await client.provision_workspace(
        user_email="john@example.com",
        user_password="password",
        template=WorkspaceTemplate.PYTHON,
    )

    print(f"User: {result.user.username}")
    print(f"Workspace: {result.workspace.name}")
```

### 3. FastAPI Integration

```python
from computor_coder import create_coder_router

# Create router with user info dependencies
router = create_coder_router(
    get_current_user_email=get_email_dependency,
    get_current_user_fullname=get_fullname_dependency,
)

app.include_router(router, prefix="/api/v1")
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/coder/health` | GET | Health check |
| `/coder/templates` | GET | List templates |
| `/coder/workspaces/provision` | POST | Provision workspace |
| `/coder/workspaces/me` | GET | Current user's workspaces |
| `/coder/workspaces/by-email/{email}` | GET | Workspaces by email |
| `/coder/workspaces/{user}/{name}/start` | POST | Start workspace |
| `/coder/workspaces/{user}/{name}/stop` | POST | Stop workspace |

## Web Interface

The plugin includes a Jinja2-based web interface for managing workspaces through a browser.

```python
from computor_coder import create_web_router, mount_static_files

# Add web interface
web_router = create_web_router(prefix="/coder-ui", api_prefix="/coder")
app.include_router(web_router)
mount_static_files(app)
```

### Web Pages

| URL | Description |
|-----|-------------|
| `/coder-ui/` | Dashboard |
| `/coder-ui/workspaces` | Workspace management |
| `/coder-ui/templates` | Template browser |
| `/coder-ui/provision` | Create new workspace |

## Available Templates

| Template | Value | Description |
|----------|-------|-------------|
| Python 3.13 | `python3.13-workspace` | Python development workspace |
| MATLAB | `matlab-workspace` | MATLAB development workspace |

## Deployment

See `deployment/` directory for Coder server installation scripts:

```bash
cd deployment

# Install Coder server
./install.sh -D coder.example.com -P 8446 -u admin -e admin@example.com -w secret

# Stop Coder server
./stop.sh

# Create users via CLI
./create-user.sh -a admin@example.com -A adminpass -u newuser -e user@example.com -p userpass
```

## Dependencies

- `computor-types>=0.1.0`
- `httpx>=0.27.0`
- `pydantic>=2.0`
- `pydantic-settings>=2.0`
- `fastapi>=0.104.0`
