"""Auto-generated client for SubmissionGroupInterface."""

from typing import Optional, List
import httpx

from computor_types.submission_groups import (
    SubmissionGroupCreate,
    SubmissionGroupGet,
    SubmissionGroupQuery,
    SubmissionGroupUpdate,
)
from computor_client.base import BaseEndpointClient


class SubmissionGroupClient(BaseEndpointClient):
    """Client for submission-groups endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/submission-groups",
            response_model=SubmissionGroupGet,
            create_model=SubmissionGroupCreate,
            update_model=SubmissionGroupUpdate,
            query_model=SubmissionGroupQuery,
        )
