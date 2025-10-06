"""
Plugin loader for discovering and loading authentication plugins.
"""

import os
import sys
import importlib
import importlib.util
from typing import Dict, List, Optional, Type
from pathlib import Path
import logging

from .base import AuthenticationPlugin, PluginConfig, PluginMetadata

logger = logging.getLogger(__name__)


class PluginLoadError(Exception):
    """Raised when a plugin cannot be loaded."""
    pass


class PluginLoader:
    """
    Discovers and loads authentication plugins from the plugins directory.
    """
    
    def __init__(self, plugins_dir: Optional[str] = None):
        """
        Initialize plugin loader.
        
        Args:
            plugins_dir: Path to plugins directory (defaults to /plugins)
        """
        if plugins_dir is None:
            # Default to /plugins relative to project root
            self.plugins_dir = Path(__file__).parent.parent.parent.parent / "plugins"
        else:
            self.plugins_dir = Path(plugins_dir)
        
        self._loaded_plugins: Dict[str, Type[AuthenticationPlugin]] = {}
        self._plugin_instances: Dict[str, AuthenticationPlugin] = {}
    
    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in the plugins directory.
        
        Returns:
            List of discovered plugin names
        """
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return []
        
        plugins = []
        
        # Look for plugin directories
        for item in self.plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if it's a valid plugin directory
                if self._is_valid_plugin_dir(item):
                    plugins.append(item.name)
                    logger.info(f"Discovered plugin: {item.name}")
        
        return plugins
    
    def load_plugin(self, plugin_name: str) -> Type[AuthenticationPlugin]:
        """
        Load a specific plugin by name.
        
        Args:
            plugin_name: Name of the plugin to load
            
        Returns:
            Plugin class
            
        Raises:
            PluginLoadError: If plugin cannot be loaded
        """
        if plugin_name in self._loaded_plugins:
            return self._loaded_plugins[plugin_name]
        
        plugin_dir = self.plugins_dir / plugin_name
        
        if not plugin_dir.exists():
            raise PluginLoadError(f"Plugin directory not found: {plugin_dir}")
        
        if not self._is_valid_plugin_dir(plugin_dir):
            raise PluginLoadError(f"Invalid plugin directory: {plugin_dir}")
        
        # Add plugin directory to Python path
        src_dir = plugin_dir / "src"
        if src_dir.exists():
            sys.path.insert(0, str(src_dir))
        else:
            sys.path.insert(0, str(plugin_dir))
        
        try:
            # Try to import the plugin module
            plugin_module = self._import_plugin_module(plugin_name, plugin_dir)
            
            # Find the plugin class
            plugin_class = self._find_plugin_class(plugin_module)
            
            if plugin_class is None:
                raise PluginLoadError(f"No AuthenticationPlugin subclass found in {plugin_name}")
            
            self._loaded_plugins[plugin_name] = plugin_class
            logger.info(f"Successfully loaded plugin: {plugin_name}")
            
            return plugin_class
            
        except Exception as e:
            raise PluginLoadError(f"Failed to load plugin {plugin_name}: {str(e)}")
        finally:
            # Remove from path to avoid conflicts
            if src_dir.exists() and str(src_dir) in sys.path:
                sys.path.remove(str(src_dir))
            elif str(plugin_dir) in sys.path:
                sys.path.remove(str(plugin_dir))
    
    def load_all_plugins(self) -> Dict[str, Type[AuthenticationPlugin]]:
        """
        Load all discovered plugins.
        
        Returns:
            Dictionary mapping plugin names to plugin classes
        """
        plugins = {}
        
        for plugin_name in self.discover_plugins():
            try:
                plugin_class = self.load_plugin(plugin_name)
                plugins[plugin_name] = plugin_class
            except PluginLoadError as e:
                logger.error(f"Failed to load plugin {plugin_name}: {e}")
        
        return plugins
    
    async def create_plugin_instance(
        self,
        plugin_name: str,
        config: Optional[PluginConfig] = None
    ) -> AuthenticationPlugin:
        """
        Create an instance of a plugin.
        
        Args:
            plugin_name: Name of the plugin
            config: Plugin configuration (uses default if not provided)
            
        Returns:
            Plugin instance
            
        Raises:
            PluginLoadError: If plugin is not loaded
        """
        if plugin_name not in self._loaded_plugins:
            # Try to load it
            self.load_plugin(plugin_name)
        
        plugin_class = self._loaded_plugins[plugin_name]
        
        if config is None:
            config = PluginConfig()
        
        # Create instance
        instance = plugin_class(config)
        
        # Initialize the plugin
        await instance.initialize()
        
        self._plugin_instances[plugin_name] = instance
        
        return instance
    
    def get_plugin_instance(self, plugin_name: str) -> Optional[AuthenticationPlugin]:
        """
        Get a plugin instance by name.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin instance or None if not instantiated
        """
        return self._plugin_instances.get(plugin_name)
    
    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """
        Get metadata for a plugin without creating an instance.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin metadata or None if plugin not loaded
        """
        if plugin_name not in self._loaded_plugins:
            try:
                self.load_plugin(plugin_name)
            except PluginLoadError:
                return None
        
        plugin_class = self._loaded_plugins[plugin_name]
        
        # Create a temporary instance to get metadata
        temp_instance = plugin_class(PluginConfig())
        return temp_instance.metadata
    
    async def shutdown_all(self) -> None:
        """Shutdown all plugin instances."""
        for instance in self._plugin_instances.values():
            try:
                await instance.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down plugin: {e}")
        
        self._plugin_instances.clear()
    
    def _is_valid_plugin_dir(self, plugin_dir: Path) -> bool:
        """
        Check if a directory is a valid plugin directory.
        
        Args:
            plugin_dir: Path to plugin directory
            
        Returns:
            True if valid plugin directory
        """
        # Check for required files
        required_files = ["setup.py", "README.md"]
        
        for file in required_files:
            if not (plugin_dir / file).exists():
                return False
        
        # Check for source directory or __init__.py
        if not ((plugin_dir / "src").exists() or (plugin_dir / "__init__.py").exists()):
            return False
        
        return True
    
    def _import_plugin_module(self, plugin_name: str, plugin_dir: Path):
        """
        Import the plugin module.
        
        Args:
            plugin_name: Name of the plugin
            plugin_dir: Path to plugin directory
            
        Returns:
            Imported module
        """
        # Try different import strategies
        
        # Strategy 1: Import from src/<plugin_name>_plugin.py
        src_dir = plugin_dir / "src"
        if src_dir.exists():
            for suffix in ["_plugin", ""]:
                module_file = src_dir / f"{plugin_name.replace('-', '_')}{suffix}.py"
                if module_file.exists():
                    spec = importlib.util.spec_from_file_location(
                        f"{plugin_name}{suffix}",
                        module_file
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        return module
        
        # Strategy 2: Import as package
        try:
            return importlib.import_module(plugin_name.replace('-', '_'))
        except ImportError:
            pass
        
        # Strategy 3: Import from __init__.py
        init_file = plugin_dir / "__init__.py"
        if init_file.exists():
            spec = importlib.util.spec_from_file_location(plugin_name, init_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
        
        raise ImportError(f"Could not import plugin module for {plugin_name}")
    
    def _find_plugin_class(self, module) -> Optional[Type[AuthenticationPlugin]]:
        """
        Find the AuthenticationPlugin subclass in a module.
        
        Args:
            module: Plugin module
            
        Returns:
            Plugin class or None if not found
        """
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            # Check if it's a class and subclass of AuthenticationPlugin
            if (isinstance(attr, type) and 
                issubclass(attr, AuthenticationPlugin) and 
                attr is not AuthenticationPlugin):
                return attr
        
        return None