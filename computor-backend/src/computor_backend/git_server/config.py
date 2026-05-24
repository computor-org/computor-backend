from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    git_server: str = ""
    git_server_url: str = ""
    git_server_admin_username: str = ""
    git_server_admin_password: str = ""
    git_server_keycloak_client_id: str = ""
    git_server_keycloak_client_secret: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.git_server)

    @property
    def is_forgejo(self) -> bool:
        return self.git_server.lower() == "forgejo"

    @property
    def oidc_enabled(self) -> bool:
        return bool(self.enabled and self.git_server_keycloak_client_id)


@lru_cache(maxsize=1)
def get_git_server_settings() -> GitServerSettings:
    return GitServerSettings()
