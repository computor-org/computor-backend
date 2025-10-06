from typing import Optional
from computor_types.deployments import BaseDeployment
from computor_types.auth import BasicAuthConfig, GLPAuthConfig

class CLIAuthConfig(BaseDeployment):
    api_url: str
    gitlab: Optional[GLPAuthConfig] = None
    basic: Optional[BasicAuthConfig] = None