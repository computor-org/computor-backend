"""
Web interface for Coder workspace management.

This module provides Jinja2-based HTML templates for interacting with
the Coder API endpoints through a web browser.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
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
    dependencies: Optional[list] = None,
) -> APIRouter:
    """
    Create a FastAPI router for the Coder web interface.

    This router serves HTML pages that interact with the Coder API
    endpoints for workspace management.

    Args:
        prefix: URL prefix for the web interface (e.g., "/coder-ui")
        api_prefix: URL prefix for the API endpoints (e.g., "/coder")
        tags: OpenAPI tags
        dependencies: Router dependencies (e.g., auth check)

    Returns:
        Configured APIRouter instance

    Example:
        ```python
        from computor_coder import create_web_router
        from fastapi import Depends
        from my_app.auth import get_current_principal

        web_router = create_web_router(
            prefix="/coder-ui",
            api_prefix="/coder",
            dependencies=[Depends(get_current_principal)],
        )
        app.include_router(web_router)
        ```
    """
    router = APIRouter(prefix=prefix, tags=tags or ["coder-web"], dependencies=dependencies or [])

    # Initialize Jinja2 templates
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    # Version for footer
    from . import __version__

    @router.get("/", response_class=HTMLResponse, name="coder_dashboard")
    async def dashboard(request: Request):
        """Render the dashboard page."""
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "active_page": "dashboard",
                "version": __version__,
                "api_prefix": api_prefix,
            },
        )

    @router.get("/workspaces", response_class=HTMLResponse, name="coder_workspaces_page")
    async def workspaces_page(request: Request):
        """Render the workspaces management page."""
        return templates.TemplateResponse(
            "workspaces.html",
            {
                "request": request,
                "active_page": "workspaces",
                "version": __version__,
                "api_prefix": api_prefix,
            },
        )

    @router.get("/templates", response_class=HTMLResponse, name="coder_templates_page")
    async def templates_page(request: Request):
        """Render the templates listing page."""
        return templates.TemplateResponse(
            "templates.html",
            {
                "request": request,
                "active_page": "templates",
                "version": __version__,
                "api_prefix": api_prefix,
            },
        )

    @router.get("/provision", response_class=HTMLResponse, name="coder_provision_page")
    async def provision_page(request: Request):
        """Render the workspace provisioning page."""
        return templates.TemplateResponse(
            "provision.html",
            {
                "request": request,
                "active_page": "provision",
                "version": __version__,
                "api_prefix": api_prefix,
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

    This should be called after creating the FastAPI app to serve
    CSS, JavaScript, and other static assets.

    Args:
        app: FastAPI application instance
        prefix: URL prefix for static files

    Example:
        ```python
        from computor_coder.web import mount_static_files

        app = FastAPI()
        mount_static_files(app)
        ```
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
        get_current_principal: Dependency for authentication
        get_user_email: Dependency for user email
        get_user_fullname: Dependency for user full name
        require_admin: Dependency for admin check

    Returns:
        Tuple of (api_router, admin_router, web_router)

    Example:
        ```python
        from computor_coder.web import create_web_app_with_api

        api, admin, web = create_web_app_with_api(
            get_current_principal=get_current_principal,
            get_user_email=get_user_email,
        )
        app.include_router(api)
        app.include_router(admin)
        app.include_router(web)
        mount_static_files(app)
        ```
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
    )

    return api_router, admin_router, web_router
