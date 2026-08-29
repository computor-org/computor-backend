"""
Plugin registry for managing authentication plugins.
"""

import asyncio
import time
from typing import Dict, List, Optional, Set
from pathlib import Path
import json
import logging

from .base import AuthenticationPlugin, PluginConfig, PluginMetadata, AuthResult, UserInfo
from .loader import PluginLoader, PluginLoadError

logger = logging.getLogger(__name__)

# Import built-in providers if available
try:
    from computor_backend.auth.providers import BUILTIN_PROVIDERS
except ImportError as e:
    logger.warning(f"Failed to import BUILTIN_PROVIDERS: {e}")
    BUILTIN_PROVIDERS = {}


class PluginRegistry:
    """
    Central registry for authentication plugins.
    
    Manages plugin lifecycle, configuration, and provides a unified interface
    for authentication operations.
    """

    # A provider whose service was unreachable at startup stays registered but
    # unusable; ensure_plugin_ready retries it on demand. Bounded on both sides
    # so a provider that is genuinely down cannot turn every login into a stall:
    # at most one attempt per cooldown window, each capped by the timeout.
    READINESS_RETRY_COOLDOWN = 30.0
    READINESS_RETRY_TIMEOUT = 15.0

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize plugin registry.
        
        Args:
            config_file: Path to plugin configuration file
        """
        self.loader = PluginLoader()
        self._plugins: Dict[str, AuthenticationPlugin] = {}
        self._enabled_plugins: Set[str] = set()
        self._config_file = config_file or self._get_default_config_path()
        self._configs: Dict[str, PluginConfig] = {}
        # Per-plugin on-demand re-initialization state (see ensure_plugin_ready).
        self._readiness_locks: Dict[str, asyncio.Lock] = {}
        self._last_readiness_attempt: Dict[str, float] = {}

    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        return str(Path(__file__).parent.parent.parent.parent / "data" / "auth_plugins.json")
    
    async def initialize(self) -> None:
        """
        Initialize the plugin registry.
        
        Loads configuration and initializes all enabled plugins.
        """
        # Load configuration
        self.load_configuration()
        
        # Discover and load plugins
        await self.load_plugins()
    
    def load_configuration(self) -> None:
        """Load plugin configuration from file."""
        config_path = Path(self._config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                for plugin_name, plugin_config in config_data.items():
                    self._configs[plugin_name] = PluginConfig(**plugin_config)
                    if plugin_config.get('enabled', True):
                        self._enabled_plugins.add(plugin_name)
                
                logger.info(f"Loaded configuration for {len(self._configs)} plugins")
            except Exception as e:
                logger.error(f"Failed to load plugin configuration: {e}")
        else:
            logger.warning(f"Plugin configuration file not found: {config_path}")
    
    def save_configuration(self) -> None:
        """Save current plugin configuration to file."""
        config_path = Path(self._config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = {}
        for plugin_name, config in self._configs.items():
            config_data[plugin_name] = config.model_dump()
        
        try:
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            logger.info(f"Saved configuration for {len(config_data)} plugins")
        except Exception as e:
            logger.error(f"Failed to save plugin configuration: {e}")
    
    async def load_plugins(self) -> None:
        """Load all enabled plugins."""
        logger.info(f"Loading plugins from {len(BUILTIN_PROVIDERS)} built-in providers")
        
        # First, load built-in providers
        for provider_name in BUILTIN_PROVIDERS:
            if provider_name in self._enabled_plugins:
                try:
                    await self.load_builtin_provider(provider_name)
                except Exception as e:
                    logger.error(f"Failed to load built-in provider {provider_name}: {e}")
        
        # Then, load external plugins
        discovered = self.loader.discover_plugins()
        logger.info(f"Discovered {len(discovered)} external plugins")
        
        for plugin_name in discovered:
            if plugin_name in self._enabled_plugins:
                try:
                    await self.load_plugin(plugin_name)
                except Exception as e:
                    logger.error(f"Failed to load plugin {plugin_name}: {e}")
    
    async def load_builtin_provider(self, provider_name: str) -> None:
        """
        Load and initialize a built-in provider.
        
        Args:
            provider_name: Name of the built-in provider to load
        """
        if provider_name in self._plugins:
            logger.warning(f"Provider {provider_name} already loaded")
            return
        
        if provider_name not in BUILTIN_PROVIDERS:
            raise ValueError(f"Built-in provider not found: {provider_name}")
        
        try:
            # Get configuration for this provider
            config = self._configs.get(provider_name, PluginConfig())
            
            # Create provider instance
            provider_class = BUILTIN_PROVIDERS[provider_name]
            provider = provider_class(config)
            
            # Initialize the provider
            await provider.initialize()
            
            self._plugins[provider_name] = provider
            logger.info(f"Successfully loaded built-in provider: {provider_name}")
            
        except Exception as e:
            logger.error(f"Failed to load built-in provider {provider_name}: {e}")
            # For keycloak, transport errors are transient — don't raise so the server continues.
            # The login endpoint will retry lazy-loading on the first request.
            if provider_name == "keycloak":
                logger.warning(f"Keycloak provider not loaded — will retry on demand")
            else:
                raise
    
    async def load_plugin(self, plugin_name: str) -> None:
        """
        Load and initialize a specific plugin.
        
        Args:
            plugin_name: Name of the plugin to load
        """
        if plugin_name in self._plugins:
            logger.warning(f"Plugin {plugin_name} already loaded")
            return
        
        try:
            # Get configuration for this plugin
            config = self._configs.get(plugin_name, PluginConfig())
            
            # Create plugin instance
            plugin = await self.loader.create_plugin_instance(plugin_name, config)
            
            self._plugins[plugin_name] = plugin
            logger.info(f"Successfully loaded and initialized plugin: {plugin_name}")
            
        except PluginLoadError as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            raise
    
    async def unload_plugin(self, plugin_name: str) -> None:
        """
        Unload and shutdown a plugin.
        
        Args:
            plugin_name: Name of the plugin to unload
        """
        if plugin_name not in self._plugins:
            return
        
        plugin = self._plugins[plugin_name]
        
        try:
            await plugin.shutdown()
            del self._plugins[plugin_name]
            self._enabled_plugins.discard(plugin_name)
            logger.info(f"Successfully unloaded plugin: {plugin_name}")
        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {e}")
    
    def get_plugin(self, plugin_name: str) -> Optional[AuthenticationPlugin]:
        """
        Get a plugin instance by name.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin instance or None if not loaded
        """
        return self._plugins.get(plugin_name)

    def plugin_is_usable(self, plugin: AuthenticationPlugin) -> bool:
        """Whether a loaded plugin can actually serve requests.

        Providers that depend on an external service expose ``is_available``
        (Keycloak reports False until it has fetched its OIDC configuration).
        Providers that don't are usable as soon as they are loaded.
        """
        return bool(getattr(plugin, "is_available", True))

    async def ensure_plugin_ready(self, plugin_name: str) -> Optional[AuthenticationPlugin]:
        """Return a plugin that is ready to serve requests, or None.

        An enabled plugin can be unusable in two ways: never loaded, or loaded
        while its backing service was down. The second one used to be permanent.
        ``KeycloakAuthPlugin.initialize`` deliberately swallows transport errors
        so the API can start without Keycloak, which leaves the plugin registered
        but holding no OIDC configuration — and nothing ever retried it, so every
        login failed with "Plugin not initialized" until the API was restarted.

        Retry here instead, on the request that needs the provider. One attempt
        at a time, at most one per cooldown window, each capped by a timeout: a
        provider that is really down returns None quickly rather than making the
        caller wait out the plugin's own connect retries.
        """
        if plugin_name not in self._enabled_plugins:
            return None

        plugin = self._plugins.get(plugin_name)
        if plugin is not None and self.plugin_is_usable(plugin):
            return plugin

        lock = self._readiness_locks.setdefault(plugin_name, asyncio.Lock())
        async with lock:
            # A concurrent request may have healed it while we waited.
            plugin = self._plugins.get(plugin_name)
            if plugin is not None and self.plugin_is_usable(plugin):
                return plugin

            now = time.monotonic()
            last_attempt = self._last_readiness_attempt.get(plugin_name)
            if last_attempt is not None and now - last_attempt < self.READINESS_RETRY_COOLDOWN:
                return None
            self._last_readiness_attempt[plugin_name] = now

            try:
                if plugin is None:
                    load = (
                        self.load_builtin_provider(plugin_name)
                        if plugin_name in BUILTIN_PROVIDERS
                        else self.load_plugin(plugin_name)
                    )
                    await asyncio.wait_for(load, self.READINESS_RETRY_TIMEOUT)
                else:
                    await asyncio.wait_for(plugin.initialize(), self.READINESS_RETRY_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning(
                    f"Timed out re-initializing auth provider {plugin_name} "
                    f"after {self.READINESS_RETRY_TIMEOUT}s"
                )
            except Exception as e:
                logger.warning(f"Auth provider {plugin_name} is still unavailable: {e}")

            plugin = self._plugins.get(plugin_name)
            if plugin is not None and self.plugin_is_usable(plugin):
                logger.info(f"Auth provider {plugin_name} is ready again (recovered on demand)")
                return plugin
            return None

    def get_enabled_plugins(self) -> List[str]:
        """Get list of enabled plugin names."""
        return list(self._enabled_plugins)
    
    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin names."""
        return list(self._plugins.keys())
    
    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """
        Get metadata for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin metadata or None if not loaded
        """
        plugin = self._plugins.get(plugin_name)
        if plugin:
            return plugin.metadata
        
        # Try to get metadata without loading
        return self.loader.get_plugin_metadata(plugin_name)
    
    def get_all_metadata(self) -> Dict[str, PluginMetadata]:
        """Get metadata for all loaded plugins."""
        metadata = {}
        for name, plugin in self._plugins.items():
            metadata[name] = plugin.metadata
        return metadata
    
    def enable_plugin(self, plugin_name: str) -> None:
        """
        Enable a plugin.
        
        Args:
            plugin_name: Name of the plugin to enable
        """
        self._enabled_plugins.add(plugin_name)
        if plugin_name not in self._configs:
            self._configs[plugin_name] = PluginConfig(enabled=True)
        else:
            self._configs[plugin_name].enabled = True
        self.save_configuration()
    
    def disable_plugin(self, plugin_name: str) -> None:
        """
        Disable a plugin.
        
        Args:
            plugin_name: Name of the plugin to disable
        """
        self._enabled_plugins.discard(plugin_name)
        if plugin_name in self._configs:
            self._configs[plugin_name].enabled = False
        else:
            self._configs[plugin_name] = PluginConfig(enabled=False)
        self.save_configuration()
    
    def update_plugin_config(self, plugin_name: str, config: PluginConfig) -> None:
        """
        Update configuration for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            config: New configuration
        """
        self._configs[plugin_name] = config
        if config.enabled:
            self._enabled_plugins.add(plugin_name)
        else:
            self._enabled_plugins.discard(plugin_name)
        self.save_configuration()
    
    async def reload_plugin(self, plugin_name: str) -> None:
        """
        Reload a plugin with current configuration.
        
        Args:
            plugin_name: Name of the plugin to reload
        """
        await self.unload_plugin(plugin_name)
        await self.load_plugin(plugin_name)
    
    async def reload_all(self) -> None:
        """Reload all plugins."""
        # Unload all plugins
        plugin_names = list(self._plugins.keys())
        for plugin_name in plugin_names:
            await self.unload_plugin(plugin_name)
        
        # Reload configuration and plugins
        self.load_configuration()
        await self.load_plugins()
    
    async def shutdown(self) -> None:
        """Shutdown all plugins and cleanup."""
        plugin_names = list(self._plugins.keys())
        
        # Shutdown all plugins
        shutdown_tasks = []
        for plugin_name in plugin_names:
            shutdown_tasks.append(self.unload_plugin(plugin_name))
        
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        logger.info("Plugin registry shutdown complete")
    
    # Authentication operations using plugins
    
    async def authenticate(self, provider: str, credentials: Dict[str, any]) -> AuthResult:
        """
        Authenticate using a specific provider.
        
        Args:
            provider: Provider/plugin name
            credentials: Authentication credentials
            
        Returns:
            Authentication result
            
        Raises:
            ValueError: If provider not found or not enabled
        """
        plugin = self.get_plugin(provider)
        if not plugin:
            raise ValueError(f"Authentication provider not found or not enabled: {provider}")
        
        return await plugin.authenticate(credentials)
    
    async def get_user_info(self, provider: str, access_token: str) -> UserInfo:
        """
        Get user information from a provider.
        
        Args:
            provider: Provider/plugin name
            access_token: Valid access token
            
        Returns:
            User information
            
        Raises:
            ValueError: If provider not found or not enabled
        """
        plugin = self.get_plugin(provider)
        if not plugin:
            raise ValueError(f"Authentication provider not found or not enabled: {provider}")
        
        return await plugin.get_user_info(access_token)
    
    def get_login_url(self, provider: str, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Get login URL for a provider.
        
        Args:
            provider: Provider/plugin name
            redirect_uri: Redirect URI after authentication
            state: Optional state parameter
            
        Returns:
            Login URL
            
        Raises:
            ValueError: If provider not found or not enabled
        """
        plugin = self.get_plugin(provider)
        if not plugin:
            raise ValueError(f"Authentication provider not found or not enabled: {provider}")
        
        return plugin.get_login_url(redirect_uri, state)
    
    async def handle_callback(self, provider: str, code: str, state: Optional[str] = None, redirect_uri: Optional[str] = None) -> AuthResult:
        """
        Handle OAuth callback for a provider.
        
        Args:
            provider: Provider/plugin name
            code: Authorization code
            state: Optional state parameter
            redirect_uri: Redirect URI used in the original authorization request
            
        Returns:
            Authentication result
            
        Raises:
            ValueError: If provider not found or not enabled
        """
        plugin = self.get_plugin(provider)
        if not plugin:
            raise ValueError(f"Authentication provider not found or not enabled: {provider}")
        
        return await plugin.handle_callback(code, state, redirect_uri)


# Global registry instance
_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry instance."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
        logger.debug("Created new plugin registry instance (not initialized)")
    return _registry


async def initialize_plugin_registry(config_file: Optional[str] = None) -> PluginRegistry:
    """
    Initialize the global plugin registry.
    
    Args:
        config_file: Optional configuration file path
        
    Returns:
        Initialized registry
    """
    global _registry
    _registry = PluginRegistry(config_file)
    await _registry.initialize()
    logger.info(f"Plugin registry initialized with {len(_registry.get_enabled_plugins())} enabled plugins: {_registry.get_enabled_plugins()}")
    return _registry