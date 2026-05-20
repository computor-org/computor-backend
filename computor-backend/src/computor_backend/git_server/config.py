from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    git_server: str = ""
    forgejo_url: str = "http://localhost:3030"
    forgejo_admin_username: str = ""
    forgejo_admin_password: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.git_server)

    @property
    def is_forgejo(self) -> bool:
        return self.git_server.lower() == "forgejo"


@lru_cache(maxsize=1)
def get_git_server_settings() -> GitServerSettings:
    return GitServerSettings()
