"""
Configuration settings for Coder integration.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .schemas import WorkspaceTemplate


class CoderSettings(BaseSettings):
    """
    Configuration for Coder API client.

    Settings are loaded from environment variables with CODER_ prefix.
    Example: CODER_URL, CODER_ADMIN_EMAIL, etc.
    """

    model_config = SettingsConfigDict(
        env_prefix="CODER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Coder server configuration
    url: str = Field(
        default="http://localhost:8446",
        description="Coder server URL"
    )

    # Admin credentials (same as backend admin)
    admin_email: str = Field(
        ...,
        description="Admin email for Coder API authentication"
    )
    admin_password: str = Field(
        ...,
        description="Admin password for Coder API authentication"
    )

    # Traefik protection header (from install.sh)
    admin_api_secret: Optional[str] = Field(
        default=None,
        description="X-Admin-Secret header value for protected endpoints"
    )

    # Default settings
    default_template: WorkspaceTemplate = Field(
        default=WorkspaceTemplate.PYTHON,
        description="Default workspace template"
    )

    # Plugin enable flag
    enabled: bool = Field(
        default=True,
        description="Whether Coder integration is enabled"
    )

    # HTTP client settings
    timeout: float = Field(
        default=30.0,
        description="HTTP request timeout in seconds"
    )
    workspace_timeout: float = Field(
        default=120.0,
        description="Timeout for workspace operations (create/start/stop)"
    )

    # Retry settings
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed requests"
    )
    retry_delay: float = Field(
        default=1.0,
        description="Delay between retries in seconds"
    )


# Singleton instance
_settings: Optional[CoderSettings] = None


@lru_cache
def get_coder_settings() -> CoderSettings:
    """
    Get Coder settings singleton.

    Uses lru_cache to ensure settings are only loaded once.

    Returns:
        CoderSettings instance

    Raises:
        ValidationError: If required settings are missing
    """
    return CoderSettings()


def configure_coder_settings(
    url: Optional[str] = None,
    admin_email: Optional[str] = None,
    admin_password: Optional[str] = None,
    admin_api_secret: Optional[str] = None,
    **kwargs,
) -> CoderSettings:
    """
    Configure Coder settings programmatically.

    This allows overriding environment variables for testing
    or when settings come from a different source.

    Args:
        url: Coder server URL
        admin_email: Admin email
        admin_password: Admin password
        admin_api_secret: X-Admin-Secret header value
        **kwargs: Additional settings

    Returns:
        Configured CoderSettings instance
    """
    global _settings

    # Build settings dict, filtering None values
    settings_dict = {
        k: v for k, v in {
            "url": url,
            "admin_email": admin_email,
            "admin_password": admin_password,
            "admin_api_secret": admin_api_secret,
            **kwargs,
        }.items() if v is not None
    }

    _settings = CoderSettings(**settings_dict)

    # Clear the lru_cache so get_coder_settings returns new settings
    get_coder_settings.cache_clear()

    return _settings


def reset_coder_settings() -> None:
    """Reset settings to default (reload from environment)."""
    global _settings
    _settings = None
    get_coder_settings.cache_clear()
