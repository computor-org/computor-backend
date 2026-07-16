"""Centralised application configuration (pydantic-settings).

A single, typed home for backend configuration that replaces scattered
``os.environ.get`` reads. Follows the same pydantic-settings pattern already
used by ``coder/config.py`` and ``git_server/config.py``.

Scope note (TASK-113): this currently hosts the object-storage size limits
(migrated here from ``storage_config.py``). The connection settings — Postgres
in ``database.py``, Redis in ``redis_cache.py``, MinIO in ``minio_client.py`` —
and the app-flag singleton in ``settings.py`` are the next domains to fold onto
``get_settings()``. That migration is deferred deliberately: it changes
prod-critical, import-order-sensitive initialisation (engines/clients are
constructed at import time) and, per the review, needs a container-boot check
plus care that no pydantic default/coercion drifts from the current raw reads.
Migrate one domain at a time behind ``get_settings()``, keeping the existing
module-level names as shims (as done for storage below).
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    """Object-storage size limits.

    Env variable names are preserved verbatim from the former
    ``storage_config.py`` module-level reads, so behaviour is unchanged.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_upload_size: int = Field(
        default=10 * 1024 * 1024,
        validation_alias="MINIO_MAX_UPLOAD_SIZE",
        description="Maximum single-file upload size in bytes (default 10 MiB).",
    )
    max_storage_per_user: int = Field(
        default=1024 * 1024 * 1024,
        validation_alias="MAX_STORAGE_PER_USER",
        description="Maximum total storage per user in bytes (default 1 GiB).",
    )
    max_storage_per_course: int = Field(
        default=10 * 1024 * 1024 * 1024,
        validation_alias="MAX_STORAGE_PER_COURSE",
        description="Maximum total storage per course in bytes (default 10 GiB).",
    )


class UpdateSettings(BaseSettings):
    """Self-update subsystem configuration (System -> Updates admin page).

    ``git_commit``/``git_branch`` are baked into the images at build time by
    computor.sh (see docker/base/Dockerfile); in dev they are unset and the
    update API falls back to reading the working tree's git metadata.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(
        default=False,
        validation_alias="UPDATE_ENABLED",
        description="Whether the self-update subsystem (updater sidecar + trigger endpoint) is enabled.",
    )
    repo_url: str = Field(
        default="",
        validation_alias="SYSTEM_REPO_URL",
        description="Git URL of the deployment repository the update check compares against.",
    )
    repo_branch: str = Field(
        default="main",
        validation_alias="SYSTEM_REPO_BRANCH",
        description="Branch the deployment tracks for updates.",
    )
    repo_token: str = Field(
        default="",
        validation_alias="SYSTEM_REPO_TOKEN",
        description="Access token for private repositories (never logged or returned).",
    )
    git_commit: str = Field(
        default="",
        validation_alias="GIT_COMMIT",
        description="Commit hash baked into the running image at build time.",
    )
    git_branch: str = Field(
        default="",
        validation_alias="GIT_BRANCH",
        description="Branch name baked into the running image at build time.",
    )


class Settings:
    """Aggregate accessor for the backend's configuration domains.

    As each domain is migrated off its ad-hoc ``os.environ`` reads, add its
    pydantic-settings object here (e.g. ``self.database``, ``self.redis``,
    ``self.minio``, ``self.app``). Consumers reach it through the cached
    ``get_settings()``.
    """

    def __init__(self) -> None:
        self.storage = StorageSettings()
        self.update = UpdateSettings()


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached ``Settings`` (built once, on first use)."""
    return Settings()
