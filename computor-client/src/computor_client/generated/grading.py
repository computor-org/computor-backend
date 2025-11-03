"""Auto-generated client for SubmissionGroupGradingInterface."""

from typing import Optional, List
import httpx

from computor_types.grading import (
    SubmissionGroupGradingCreate,
    SubmissionGroupGradingGet,
    SubmissionGroupGradingQuery,
    SubmissionGroupGradingUpdate,
)
from computor_client.base import BaseEndpointClient


class SubmissionGroupGradingClient(BaseEndpointClient):
    """Client for submission-group-gradings endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/submission-group-gradings",
            response_model=SubmissionGroupGradingGet,
            create_model=SubmissionGroupGradingCreate,
            update_model=SubmissionGroupGradingUpdate,
            query_model=SubmissionGroupGradingQuery,
        )
