"""
Web interface for Coder workspace management.

This module provides Jinja2-based HTML templates for interacting with
the Coder API endpoints through a web browser.

Unauthenticated requests to protected pages are redirected to the login page.
"""

import logging
from pathlib import Path
from typing import Callable, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

# Get the package directory
PACKAGE_DIR = Path(__file__).parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"


def create_web_router(
    prefix: str = "/coder-ui",
    api_prefix: str = "/coder",
    tags: Optional[list[str]] = None,
    get_current_principal_optional: Optional[Callable] = None,
) -> APIRouter:
    """
    Create a FastAPI router for the Coder web interface.

    This router serves HTML pages that interact with the Coder API
    endpoints for workspace management. Unauthenticated users are
    redirected to the login page.

    Args:
        prefix: URL prefix for the web interface (e.g., "/coder-ui")
        api_prefix: URL prefix for the API endpoints (e.g., "/coder")
        tags: OpenAPI tags
        get_current_principal_optional: Auth dependency that returns None
            instead of raising on failure. When provided, unauthenticated
            requests are redirected to the login page.

    Returns:
        Configured APIRouter instance

    Example:
        ```python
        from computor_coder import create_web_router
        from my_app.auth import get_current_principal_optional

        web_router = create_web_router(
            prefix="/coder-ui",
            api_prefix="/coder",
            get_current_principal_optional=get_current_principal_optional,
        )
        app.include_router(web_router)
        ```
    """
    router = APIRouter(prefix=prefix, tags=tags or ["coder-web"])

    # Initialize Jinja2 templates
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    # Version for footer
    from . import __version__

    # Auth dependency: returns principal or None (never raises)
    if get_current_principal_optional is not None:
        async def get_principal(
            request: Request,
            principal=Depends(get_current_principal_optional),
        ):
            return principal
    else:
        async def get_principal(request: Request):
            return None

    def _login_redirect(request: Request) -> RedirectResponse:
        """Build a redirect response to the login page with ?next= param."""
        return RedirectResponse(f"{prefix}/login?next={request.url.path}")

    @router.get("/", response_class=HTMLResponse, name="coder_dashboard")
    async def dashboard(request: Request, principal=Depends(get_principal)):
        """Render the dashboard page."""
        if principal is None:
            return _login_redirect(request)
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "active_page": "dashboard",
                "version": __version__,
                "api_prefix": api_prefix,
                "principal": principal,
            },
        )

    @router.get("/workspaces", response_class=HTMLResponse, name="coder_workspaces_page")
    async def workspaces_page(request: Request, principal=Depends(get_principal)):
        """Render the workspaces management page."""
        if principal is None:
            return _login_redirect(request)
        return templates.TemplateResponse(
            "workspaces.html",
            {
                "request": request,
                "active_page": "workspaces",
                "version": __version__,
                "api_prefix": api_prefix,
                "principal": principal,
            },
        )

    @router.get("/templates", response_class=HTMLResponse, name="coder_templates_page")
    async def templates_page(request: Request, principal=Depends(get_principal)):
        """Render the templates listing page."""
        if principal is None:
            return _login_redirect(request)
        return templates.TemplateResponse(
            "templates.html",
            {
                "request": request,
                "active_page": "templates",
                "version": __version__,
                "api_prefix": api_prefix,
                "principal": principal,
            },
        )

    @router.get("/provision", response_class=HTMLResponse, name="coder_provision_page")
    async def provision_page(request: Request, principal=Depends(get_principal)):
        """Render the workspace provisioning page."""
        if principal is None:
            return _login_redirect(request)
        return templates.TemplateResponse(
            "provision.html",
            {
                "request": request,
                "active_page": "provision",
                "version": __version__,
                "api_prefix": api_prefix,
                "principal": principal,
            },
        )

    return router


def create_login_router(
    prefix: str = "/coder-ui",
    tags: Optional[list[str]] = None,
) -> APIRouter:
    """
    Create a public router for the login page (no auth required).

    Args:
        prefix: URL prefix for the web interface
        tags: OpenAPI tags

    Returns:
        APIRouter with login endpoint
    """
    router = APIRouter(prefix=prefix, tags=tags or ["coder-web"])

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    from . import __version__

    @router.get("/login", response_class=HTMLResponse, name="coder_login_page")
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

    return router


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


def create_web_app_with_api(
    api_prefix: str = "/coder",
    web_prefix: str = "/coder-ui",
    get_current_principal=None,
    get_current_principal_optional=None,
    get_user_email=None,
    get_user_fullname=None,
    require_admin=None,
):
    """
    Create a combined FastAPI app with both API and web interface.

    This is a convenience function for standalone deployment.

    Args:
        api_prefix: URL prefix for API endpoints
        web_prefix: URL prefix for web interface
        get_current_principal: Dependency for authentication (raises on failure)
        get_current_principal_optional: Dependency for authentication (returns None on failure)
        get_user_email: Dependency for user email
        get_user_fullname: Dependency for user full name
        require_admin: Dependency for admin check

    Returns:
        Tuple of (api_router, admin_router, web_router, login_router)
    """
    from .router import create_admin_coder_router, create_coder_router

    api_router = create_coder_router(
        prefix=api_prefix,
        tags=["coder", "workspaces"],
        get_current_principal=get_current_principal,
        get_user_email=get_user_email,
        get_user_fullname=get_user_fullname,
    )

    admin_router = create_admin_coder_router(
        prefix=f"/admin{api_prefix}",
        tags=["coder-admin"],
        get_current_principal=get_current_principal,
        require_admin=require_admin,
    )

    web_router = create_web_router(
        prefix=web_prefix,
        api_prefix=api_prefix,
        tags=["coder-web"],
        get_current_principal_optional=get_current_principal_optional,
    )

    login_router = create_login_router(
        prefix=web_prefix,
        tags=["coder-web"],
    )

    return api_router, admin_router, web_router, login_router
