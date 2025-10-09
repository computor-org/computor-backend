"""
Tests for the authentication plugin system.
"""

import pytest
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from computor_backend.plugins import (
    AuthenticationPlugin,
    AuthResult,
    UserInfo,
    PluginConfig,
    PluginMetadata,
    AuthStatus,
    AuthenticationType
)
from computor_backend.plugins.loader import PluginLoader, PluginLoadError
from computor_backend.plugins.registry import PluginRegistry


class MockAuthPlugin(AuthenticationPlugin):
    """Mock authentication plugin for testing."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="mock-auth",
            version="1.0.0",
            description="Mock authentication plugin for testing",
            author="Test Author",
            provider_name="Mock Provider",
            provider_type=AuthenticationType.OAUTH2,
            requires=["requests", "pydantic"]
        )
    
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """Mock authentication."""
        if credentials.get("username") == "test" and credentials.get("password") == "password":
            return AuthResult(
                status=AuthStatus.SUCCESS,
                user_info=UserInfo(
                    provider_id="mock-123",
                    email="test@example.com",
                    username="test",
                    given_name="Test",
                    family_name="User",
                    full_name="Test User"
                ),
                access_token="mock-access-token",
                refresh_token="mock-refresh-token",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
        else:
            return AuthResult(
                status=AuthStatus.FAILED,
                error_message="Invalid credentials"
            )
    
    async def get_user_info(self, access_token: str) -> UserInfo:
        """Mock get user info."""
        if access_token == "mock-access-token":
            return UserInfo(
                provider_id="mock-123",
                email="test@example.com",
                username="test",
                given_name="Test",
                family_name="User",
                full_name="Test User"
            )
        else:
            raise Exception("Invalid access token")
    
    def get_login_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """Mock login URL generation."""
        url = f"https://mock-provider.com/oauth/authorize?redirect_uri={redirect_uri}"
        if state:
            url += f"&state={state}"
        return url
    
    async def handle_callback(self, code: str, state: Optional[str] = None) -> AuthResult:
        """Mock OAuth callback handling."""
        if code == "valid-code":
            return await self.authenticate({"username": "test", "password": "password"})
        else:
            return AuthResult(
                status=AuthStatus.FAILED,
                error_message="Invalid authorization code"
            )


class TestPluginBase:
    """Test base plugin functionality."""
    
    def test_plugin_metadata(self):
        """Test plugin metadata."""
        plugin = MockAuthPlugin(PluginConfig())
        metadata = plugin.metadata
        
        assert metadata.name == "mock-auth"
        assert metadata.version == "1.0.0"
        assert metadata.provider_type == AuthenticationType.OAUTH2
        assert metadata.provider_name == "Mock Provider"
    
    @pytest.mark.asyncio
    async def test_plugin_initialization(self):
        """Test plugin initialization."""
        plugin = MockAuthPlugin(PluginConfig())
        
        assert not plugin.is_initialized()
        
        await plugin.initialize()
        assert plugin.is_initialized()
        
        await plugin.shutdown()
        assert not plugin.is_initialized()
    
    @pytest.mark.asyncio
    async def test_authentication(self):
        """Test authentication flow."""
        plugin = MockAuthPlugin(PluginConfig())
        await plugin.initialize()
        
        # Test successful authentication
        result = await plugin.authenticate({
            "username": "test",
            "password": "password"
        })
        
        assert result.status == AuthStatus.SUCCESS
        assert result.user_info is not None
        assert result.user_info.email == "test@example.com"
        assert result.access_token == "mock-access-token"
        
        # Test failed authentication
        result = await plugin.authenticate({
            "username": "wrong",
            "password": "wrong"
        })
        
        assert result.status == AuthStatus.FAILED
        assert result.error_message == "Invalid credentials"
    
    @pytest.mark.asyncio
    async def test_get_user_info(self):
        """Test getting user info."""
        plugin = MockAuthPlugin(PluginConfig())
        await plugin.initialize()
        
        # Test valid token
        user_info = await plugin.get_user_info("mock-access-token")
        assert user_info.provider_id == "mock-123"
        assert user_info.email == "test@example.com"
        
        # Test invalid token
        with pytest.raises(Exception, match="Invalid access token"):
            await plugin.get_user_info("invalid-token")
    
    def test_login_url_generation(self):
        """Test login URL generation."""
        plugin = MockAuthPlugin(PluginConfig())
        
        # Without state
        url = plugin.get_login_url("http://localhost/callback")
        assert url == "https://mock-provider.com/oauth/authorize?redirect_uri=http://localhost/callback"
        
        # With state
        url = plugin.get_login_url("http://localhost/callback", "test-state")
        assert url == "https://mock-provider.com/oauth/authorize?redirect_uri=http://localhost/callback&state=test-state"
    
    @pytest.mark.asyncio
    async def test_oauth_callback(self):
        """Test OAuth callback handling."""
        plugin = MockAuthPlugin(PluginConfig())
        await plugin.initialize()
        
        # Test valid code
        result = await plugin.handle_callback("valid-code")
        assert result.status == AuthStatus.SUCCESS
        assert result.user_info is not None
        
        # Test invalid code
        result = await plugin.handle_callback("invalid-code")
        assert result.status == AuthStatus.FAILED
        assert result.error_message == "Invalid authorization code"


class TestPluginLoader:
    """Test plugin loader functionality."""
    
    def test_plugin_discovery_empty_directory(self):
        """Test plugin discovery with empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = PluginLoader(tmpdir)
            plugins = loader.discover_plugins()
            assert plugins == []
    
    def test_plugin_discovery_invalid_plugin(self):
        """Test plugin discovery with invalid plugin structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create invalid plugin directory
            plugin_dir = Path(tmpdir) / "invalid-plugin"
            plugin_dir.mkdir()
            
            loader = PluginLoader(tmpdir)
            plugins = loader.discover_plugins()
            assert plugins == []  # Should not discover invalid plugin
    
    def test_load_nonexistent_plugin(self):
        """Test loading a plugin that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = PluginLoader(tmpdir)
            
            with pytest.raises(PluginLoadError, match="Plugin directory not found"):
                loader.load_plugin("nonexistent-plugin")
    
    def test_get_plugin_metadata(self):
        """Test getting plugin metadata without creating instance."""
        # This would require creating a proper plugin directory structure
        # For now, we'll skip the actual file-based loading test
        pass


class TestPluginRegistry:
    """Test plugin registry functionality."""
    
    @pytest.mark.asyncio
    async def test_registry_initialization(self):
        """Test registry initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "auth_plugins.json"
            
            # Create config file
            config_data = {
                "mock-auth": {
                    "enabled": True,
                    "priority": 10,
                    "settings": {"test": "value"}
                }
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f)
            
            registry = PluginRegistry(str(config_file))
            registry.load_configuration()
            
            assert "mock-auth" in registry._enabled_plugins
            assert "mock-auth" in registry._configs
            assert registry._configs["mock-auth"].priority == 10
    
    def test_enable_disable_plugin(self):
        """Test enabling and disabling plugins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "auth_plugins.json"
            registry = PluginRegistry(str(config_file))
            
            # Enable plugin
            registry.enable_plugin("test-plugin")
            assert "test-plugin" in registry._enabled_plugins
            assert registry._configs["test-plugin"].enabled
            
            # Disable plugin
            registry.disable_plugin("test-plugin")
            assert "test-plugin" not in registry._enabled_plugins
            assert not registry._configs["test-plugin"].enabled
    
    def test_update_plugin_config(self):
        """Test updating plugin configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "auth_plugins.json"
            registry = PluginRegistry(str(config_file))
            
            new_config = PluginConfig(
                enabled=True,
                priority=20,
                settings={"new": "setting"}
            )
            
            registry.update_plugin_config("test-plugin", new_config)
            
            assert registry._configs["test-plugin"].priority == 20
            assert registry._configs["test-plugin"].settings["new"] == "setting"
            assert "test-plugin" in registry._enabled_plugins
    
    @pytest.mark.asyncio
    async def test_authentication_via_registry(self):
        """Test authentication through registry."""
        # This would require mocking the plugin loading
        # For now, we'll test the error case
        registry = PluginRegistry()
        
        with pytest.raises(ValueError, match="Authentication provider not found"):
            await registry.authenticate("nonexistent", {"test": "creds"})
    
    def test_get_login_url_via_registry(self):
        """Test getting login URL through registry."""
        registry = PluginRegistry()
        
        with pytest.raises(ValueError, match="Authentication provider not found"):
            registry.get_login_url("nonexistent", "http://localhost/callback")


class TestPluginConfig:
    """Test plugin configuration."""
    
    def test_default_config(self):
        """Test default plugin configuration."""
        config = PluginConfig()
        
        assert config.enabled == True
        assert config.priority == 0
        assert config.settings == {}
    
    def test_custom_config(self):
        """Test custom plugin configuration."""
        config = PluginConfig(
            enabled=False,
            priority=10,
            settings={"key": "value"}
        )
        
        assert config.enabled == False
        assert config.priority == 10
        assert config.settings["key"] == "value"


class TestAuthTypes:
    """Test authentication types and enums."""
    
    def test_authentication_types(self):
        """Test authentication type enum."""
        assert AuthenticationType.OAUTH2.value == "oauth2"
        assert AuthenticationType.OIDC.value == "oidc"
        assert AuthenticationType.SAML.value == "saml"
        assert AuthenticationType.LDAP.value == "ldap"
        assert AuthenticationType.CUSTOM.value == "custom"
    
    def test_auth_status(self):
        """Test authentication status enum."""
        assert AuthStatus.SUCCESS.value == "success"
        assert AuthStatus.FAILED.value == "failed"
        assert AuthStatus.PENDING.value == "pending"
        assert AuthStatus.ERROR.value == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])