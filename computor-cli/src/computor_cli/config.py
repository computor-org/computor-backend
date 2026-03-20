from typing import Optional
from pydantic import BaseModel
from computor_types.deployments_refactored import BaseDeployment


class CredentialsAuth(BaseModel):
    username: str
    password: str


class ApiTokenAuth(BaseModel):
    token: str


class CLIAuthConfig(BaseDeployment):
    api_url: str
    credentials: Optional[CredentialsAuth] = None
    api_token: Optional[ApiTokenAuth] = None
