"""
Built-in authentication providers registry.
"""

from typing import Dict, Type
from computor_backend.plugins.base import AuthenticationPlugin
from .keycloak import KeycloakAuthPlugin


# Registry of built-in authentication providers
BUILTIN_PROVIDERS: Dict[str, Type[AuthenticationPlugin]] = {
    "keycloak": KeycloakAuthPlugin,
}


def get_builtin_provider(name: str) -> Type[AuthenticationPlugin]:
    """
    Get a built-in authentication provider by name.
    
    Args:
        name: Provider name
        
    Returns:
        Provider class
        
    Raises:
        KeyError: If provider not found
    """
    if name not in BUILTIN_PROVIDERS:
        raise KeyError(f"Built-in provider not found: {name}")
    
    return BUILTIN_PROVIDERS[name]