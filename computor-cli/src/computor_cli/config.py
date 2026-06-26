from typing import Optional
from computor_types.deployments_refactored import BaseDeployment


class CLIAuthConfig(BaseDeployment):
    api_url: str
    token: Optional[str] = None
