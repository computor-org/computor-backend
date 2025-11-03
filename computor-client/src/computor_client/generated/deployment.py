"""Auto-generated client for CourseContentDeploymentInterface."""

from typing import Optional, List
import httpx

from computor_types.deployment import (
    CourseContentDeploymentCreate,
    CourseContentDeploymentGet,
    CourseContentDeploymentQuery,
    CourseContentDeploymentUpdate,
)
from computor_client.base import BaseEndpointClient


class CourseContentDeploymentClient(BaseEndpointClient):
    """Client for deployments endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/deployments",
            response_model=CourseContentDeploymentGet,
            create_model=CourseContentDeploymentCreate,
            update_model=CourseContentDeploymentUpdate,
            query_model=CourseContentDeploymentQuery,
        )

"""Auto-generated client for DeploymentHistoryInterface."""

from typing import Optional, List
import httpx

from computor_types.deployment import (
    DeploymentHistoryCreate,
    DeploymentHistoryGet,
    ListQuery,
)
from computor_client.base import BaseEndpointClient


class DeploymentHistoryClient(BaseEndpointClient):
    """Client for deployment-history endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/deployment-history",
            response_model=DeploymentHistoryGet,
            create_model=DeploymentHistoryCreate,
            query_model=ListQuery,
        )
