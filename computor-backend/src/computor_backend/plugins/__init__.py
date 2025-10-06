"""
Authentication plugin system for Computor.
"""

from .base import (
    AuthenticationPlugin,
    AuthResult,
    UserInfo,
    PluginConfig,
    PluginMetadata,
    AuthStatus,
    AuthenticationType
)
from .registry import PluginRegistry
from .loader import PluginLoader

__all__ = [
    'AuthenticationPlugin',
    'AuthResult',
    'UserInfo',
    'PluginConfig',
    'PluginMetadata',
    'AuthStatus',
    'AuthenticationType',
    'PluginRegistry',
    'PluginLoader'
]