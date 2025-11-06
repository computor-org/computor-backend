"""Auto-generated client for SubmissionGroupMemberInterface."""

from typing import Optional, List
import httpx

from computor_types.submission_group_members import (
    SubmissionGroupMemberCreate,
    SubmissionGroupMemberGet,
    SubmissionGroupMemberQuery,
    SubmissionGroupMemberUpdate,
)
from computor_client.base import TypedEndpointClient


class SubmissionGroupMemberClient(TypedEndpointClient):
    """Client for submission-group-members endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/submission-group-members",
            response_model=SubmissionGroupMemberGet,
            create_model=SubmissionGroupMemberCreate,
            update_model=SubmissionGroupMemberUpdate,
            query_model=SubmissionGroupMemberQuery,
        )
