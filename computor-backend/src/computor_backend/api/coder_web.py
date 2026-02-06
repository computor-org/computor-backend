"""
Web interface for Coder workspace management.

This module provides Jinja2-based HTML templates for interacting with
the Coder API endpoints through a web browser.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from computor_backend.permissions.auth import get_current_principal_optional
from computor_backend.permissions.principal import Principal

logger = logging.getLogger(__name__)

# Version
__version__ = "0.1.0"

# Get the coder package directory for templates and static files
CODER_DIR = Path(__file__).parent.parent / "coder"
TEMPLATES_DIR = CODER_DIR / "templates"
STATIC_DIR = CODER_DIR / "static"

# API prefix for JavaScript to call
API_PREFIX = "/coder"
WEB_PREFIX = "/coder-ui"

# Initialize Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Create routers
router = APIRouter(prefix=WEB_PREFIX, tags=["coder-web"])
login_router = APIRouter(prefix=WEB_PREFIX, tags=["coder-web"])


def _login_redirect(request: Request) -> RedirectResponse:
    """Build a redirect response to the login page with ?next= param."""
    return RedirectResponse(f"{WEB_PREFIX}/login?next={request.url.path}")


def _has_workspace_access(principal: Optional[Principal], action: str = "access") -> bool:
    """Check if the principal has a specific workspace permission."""
    if principal is None:
        return False
    if principal.is_admin:
        return True
    if hasattr(principal, "permitted"):
        return principal.permitted("workspace", action)
    return False


def _forbidden_response(request: Request):
    """Return a 403 forbidden page for users without workspace access."""
    return templates.TemplateResponse(
        "forbidden.html",
        {
            "request": request,
            "version": __version__,
        },
        status_code=403,
    )


# -----------------------------------------------------------------------------
# Protected pages (require authentication)
# -----------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse, name="coder_dashboard")
async def dashboard(
    request: Request,
    principal: Optional[Principal] = Depends(get_current_principal_optional),
):
    """Render the dashboard page."""
    if principal is None:
        return _login_redirect(request)
    if not _has_workspace_access(principal):
        return _forbidden_response(request)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_page": "dashboard",
            "version": __version__,
            "api_prefix": API_PREFIX,
            "principal": principal,
        },
    )


@router.get("/workspaces", response_class=HTMLResponse, name="coder_workspaces_page")
async def workspaces_page(
    request: Request,
    principal: Optional[Principal] = Depends(get_current_principal_optional),
):
    """Render the workspaces management page."""
    if principal is None:
        return _login_redirect(request)
    if not _has_workspace_access(principal):
        return _forbidden_response(request)
    return templates.TemplateResponse(
        "workspaces.html",
        {
            "request": request,
            "active_page": "workspaces",
            "version": __version__,
            "api_prefix": API_PREFIX,
            "principal": principal,
        },
    )


@router.get("/templates", response_class=HTMLResponse, name="coder_templates_page")
async def templates_page(
    request: Request,
    principal: Optional[Principal] = Depends(get_current_principal_optional),
):
    """Render the templates listing page."""
    if principal is None:
        return _login_redirect(request)
    if not _has_workspace_access(principal):
        return _forbidden_response(request)
    return templates.TemplateResponse(
        "templates.html",
        {
            "request": request,
            "active_page": "templates",
            "version": __version__,
            "api_prefix": API_PREFIX,
            "principal": principal,
        },
    )


@router.get("/provision", response_class=HTMLResponse, name="coder_provision_page")
async def provision_page(
    request: Request,
    principal: Optional[Principal] = Depends(get_current_principal_optional),
):
    """Render the workspace provisioning page."""
    if principal is None:
        return _login_redirect(request)
    if not _has_workspace_access(principal):
        return _forbidden_response(request)
    if not _has_workspace_access(principal, "provision"):
        return _forbidden_response(request)
    return templates.TemplateResponse(
        "provision.html",
        {
            "request": request,
            "active_page": "provision",
            "version": __version__,
            "api_prefix": API_PREFIX,
            "principal": principal,
        },
    )


@router.get("/users", response_class=HTMLResponse, name="coder_users_page")
async def users_page(
    request: Request,
    principal: Optional[Principal] = Depends(get_current_principal_optional),
):
    """Render the workspace role management page."""
    if principal is None:
        return _login_redirect(request)
    if not _has_workspace_access(principal, "manage"):
        return _forbidden_response(request)
    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "active_page": "users",
            "version": __version__,
            "api_prefix": API_PREFIX,
            "principal": principal,
        },
    )


@router.get("/users/{user_id}", response_class=HTMLResponse, name="coder_user_detail_page")
async def user_detail_page(
    request: Request,
    user_id: str,
    principal: Optional[Principal] = Depends(get_current_principal_optional),
):
    """Render the user detail/workspace management page."""
    if principal is None:
        return _login_redirect(request)
    if not _has_workspace_access(principal, "manage"):
        return _forbidden_response(request)
    return templates.TemplateResponse(
        "user_detail.html",
        {
            "request": request,
            "active_page": "users",
            "version": __version__,
            "api_prefix": API_PREFIX,
            "principal": principal,
            "user_id": user_id,
        },
    )


# -----------------------------------------------------------------------------
# Public pages (no authentication required)
# -----------------------------------------------------------------------------

@login_router.get("/login", response_class=HTMLResponse, name="coder_login_page")
async def login_page(request: Request, next: Optional[str] = None):
    """Render the login page."""
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "active_page": "login",
            "version": __version__,
            "next": next,
        },
    )


# -----------------------------------------------------------------------------
# Static files helper
# -----------------------------------------------------------------------------

def mount_static_files(app, prefix: str = "/coder-ui/static") -> None:
    """
    Mount static files for the web interface.

    Args:
        app: FastAPI application instance
        prefix: URL prefix for static files
    """
    if STATIC_DIR.exists():
        app.mount(
            prefix,
            StaticFiles(directory=str(STATIC_DIR)),
            name="coder_static",
        )
        logger.info(f"Mounted Coder static files at {prefix}")
    else:
        logger.warning(f"Static directory not found: {STATIC_DIR}")
