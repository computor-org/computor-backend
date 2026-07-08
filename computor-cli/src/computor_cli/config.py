from typing import Optional
from computor_types.yaml_config import YamlConfig


class CLIAuthConfig(YamlConfig):
    api_url: str
    token: Optional[str] = None
