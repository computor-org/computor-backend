"""
Plugin interface for Computor backend integration.

This module provides a unified interface for integrating the Coder
functionality into the computor-backend application.
"""

import logging
from typing import Any, Callable, Optional

from fastapi import APIRouter

from .client import CoderClient, get_coder_client, reset_coder_client
from .config import CoderSettings, get_coder_settings
from .router import create_admin_coder_router, create_coder_router
from .web import create_web_router, mount_static_files

logger = logging.getLogger(__name__)


class CoderPlugin:
    """
    Service plugin for Coder workspace management.

    This class provides a unified interface for integrating Coder
    into the computor-backend. It manages the client lifecycle and
    provides access to routers and the API client.

    Example usage in computor-backend:

        ```python
        from computor_coder import CoderPlugin
        from computor_backend.permissions.auth import get_current_principal
        from computor_backend.permissions.principal import Principal
        from computor_backend.database import get_db
        from computor_backend.model.auth import User
        from fastapi import Depends
        from typing import Annotated

        # Define dependencies following backend pattern
        async def get_user_email(
            permissions: Annotated[Principal, Depends(get_current_principal)],
            db: Session = Depends(get_db),
        ) -> str:
            user = db.query(User).filter(User.id == permissions.user_id).first()
            return user.email

        async def get_user_fullname(
            permissions: Annotated[Principal, Depends(get_current_principal)],
            db: Session = Depends(get_db),
        ) -> Optional[str]:
            user = db.query(User).filter(User.id == permissions.user_id).first()
            if user.given_name and user.family_name:
                return f"{user.given_name} {user.family_name}"
            return None

        # In server.py startup
        coder = CoderPlugin()
        await coder.initialize()

        # Mount the router with permissions pattern
        app.include_router(
            coder.get_router(
                get_current_principal=get_current_principal,
                get_user_email=get_user_email,
                get_user_fullname=get_user_fullname,
            ),
        )

        # Use client in business logic
        client = coder.client
        result = await client.provision_workspace(...)

        # In shutdown
        await coder.shutdown()
        ```
    """

    def __init__(self, settings: Optional[CoderSettings] = None):
        """
        Initialize the Coder plugin.

        Args:
            settings: Optional CoderSettings. If not provided, loads from environment.
        """
        self._settings = settings
        self._client: Optional[CoderClient] = None
        self._initialized = False

    @property
    def settings(self) -> CoderSettings:
        """Get plugin settings."""
        if self._settings is None:
            self._settings = get_coder_settings()
        return self._settings

    @property
    def client(self) -> CoderClient:
        """
        Get the Coder API client.

        Returns:
            CoderClient instance

        Raises:
            RuntimeError: If plugin is not initialized
        """
        if not self._initialized:
            raise RuntimeError("CoderPlugin not initialized. Call initialize() first.")
        if self._client is None:
            self._client = get_coder_client()
        return self._client

    @property
    def is_enabled(self) -> bool:
        """Check if Coder integration is enabled."""
        return self.settings.enabled

    @property
    def is_initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._initialized

    async def initialize(self) -> bool:
        """
        Initialize the plugin.

        This performs a health check to verify Coder is reachable.

        Returns:
            True if initialization successful, False if Coder is unhealthy
        """
        if not self.is_enabled:
            logger.info("Coder integration is disabled")
            self._initialized = True
            return True

        logger.info(f"Initializing Coder plugin (URL: {self.settings.url})")

        self._client = CoderClient(self.settings)

        try:
            healthy, version = await self._client.health_check()
            if healthy:
                logger.info(f"Coder server healthy (version: {version})")
                self._initialized = True
                return True
            else:
                logger.warning("Coder server unhealthy, continuing anyway")
                self._initialized = True
                return False
        except Exception as e:
            logger.warning(f"Failed to connect to Coder: {e}. Plugin will retry on requests.")
            self._initialized = True
            return False

    async def shutdown(self) -> None:
        """Shutdown the plugin and cleanup resources."""
        logger.info("Shutting down Coder plugin")
        if self._client:
            await self._client.close()
            self._client = None
        reset_coder_client()
        self._initialized = False

    def get_router(
        self,
        prefix: str = "/coder",
        tags: Optional[list[str]] = None,
        get_current_principal: Optional[Callable] = None,
        get_user_email: Optional[Callable] = None,
        get_user_fullname: Optional[Callable] = None,
        dependencies: Optional[list] = None,
    ) -> APIRouter:
        """
        Get the FastAPI router for Coder endpoints.

        Follows the computor-backend pattern where `permissions` (Principal)
        is injected as a dependency.

        Args:
            prefix: URL prefix for the router
            tags: OpenAPI tags
            get_current_principal: Dependency to get current Principal (permissions)
            get_user_email: Dependency to get user's email
            get_user_fullname: Optional dependency for user's full name
            dependencies: Additional router dependencies

        Returns:
            Configured APIRouter instance

        Example:
            ```python
            router = coder.get_router(
                get_current_principal=get_current_principal,
                get_user_email=get_user_email,
                get_user_fullname=get_user_fullname,
            )
            ```
        """
        return create_coder_router(
            prefix=prefix,
            tags=tags,
            get_current_principal=get_current_principal,
            get_user_email=get_user_email,
            get_user_fullname=get_user_fullname,
            dependencies=dependencies,
        )

    def get_admin_router(
        self,
        prefix: str = "/admin/coder",
        tags: Optional[list[str]] = None,
        get_current_principal: Optional[Callable] = None,
        require_admin: Optional[Callable] = None,
        dependencies: Optional[list] = None,
    ) -> APIRouter:
        """
        Get the admin FastAPI router for Coder management.

        Args:
            prefix: URL prefix
            tags: OpenAPI tags
            get_current_principal: Dependency to get current Principal (permissions)
            require_admin: Optional dependency to require admin role
            dependencies: Router dependencies

        Returns:
            Configured APIRouter instance

        Example:
            ```python
            async def require_admin(
                permissions: Annotated[Principal, Depends(get_current_principal)]
            ):
                if not permissions.is_admin:
                    raise ForbiddenException("Admin access required")
                return permissions

            admin_router = coder.get_admin_router(
                get_current_principal=get_current_principal,
                require_admin=require_admin,
            )
            ```
        """
        return create_admin_coder_router(
            prefix=prefix,
            tags=tags,
            get_current_principal=get_current_principal,
            require_admin=require_admin,
            dependencies=dependencies,
        )

    def get_web_router(
        self,
        prefix: str = "/coder-ui",
        api_prefix: str = "/coder",
        tags: Optional[list[str]] = None,
    ) -> APIRouter:
        """
        Get the FastAPI router for the Coder web interface.

        This router serves HTML pages that interact with the Coder API
        endpoints for workspace management.

        Args:
            prefix: URL prefix for the web interface (e.g., "/coder-ui")
            api_prefix: URL prefix for the API endpoints (e.g., "/coder")
            tags: OpenAPI tags

        Returns:
            Configured APIRouter instance

        Example:
            ```python
            web_router = coder.get_web_router(
                prefix="/coder-ui",
                api_prefix="/coder",
            )
            app.include_router(web_router)
            coder.mount_static_files(app)
            ```
        """
        return create_web_router(
            prefix=prefix,
            api_prefix=api_prefix,
            tags=tags,
        )

    def mount_static_files(self, app, prefix: str = "/coder-ui/static") -> None:
        """
        Mount static files for the web interface.

        This should be called after including the web router to serve
        CSS, JavaScript, and other static assets.

        Args:
            app: FastAPI application instance
            prefix: URL prefix for static files

        Example:
            ```python
            app.include_router(coder.get_web_router())
            coder.mount_static_files(app)
            ```
        """
        mount_static_files(app, prefix)

    def get_metadata(self) -> dict[str, Any]:
        """Get plugin metadata."""
        return {
            "name": "coder",
            "version": "0.1.0",
            "description": "Coder workspace management integration",
            "enabled": self.is_enabled,
            "initialized": self.is_initialized,
            "url": self.settings.url if self.is_enabled else None,
        }


# Singleton instance
_plugin: Optional[CoderPlugin] = None


def get_coder_plugin() -> CoderPlugin:
    """Get or create the Coder plugin singleton."""
    global _plugin
    if _plugin is None:
        _plugin = CoderPlugin()
    return _plugin


async def initialize_coder_plugin(
    settings: Optional[CoderSettings] = None,
) -> CoderPlugin:
    """
    Initialize the Coder plugin.

    This is a convenience function for initializing the plugin
    in computor-backend startup.

    Args:
        settings: Optional settings override

    Returns:
        Initialized CoderPlugin instance
    """
    global _plugin
    _plugin = CoderPlugin(settings)
    await _plugin.initialize()
    return _plugin


def reset_coder_plugin() -> None:
    """Reset the Coder plugin singleton."""
    global _plugin
    _plugin = None
