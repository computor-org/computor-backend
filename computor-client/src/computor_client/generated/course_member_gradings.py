"""Auto-generated client for CourseMemberGradingsInterface."""

from typing import Optional, List
import httpx

from computor_types.course_member_gradings import (
    CourseMemberGradingsGet,
    CourseMemberGradingsQuery,
)
from computor_client.base import TypedEndpointClient


class CourseMemberGradingsClient(TypedEndpointClient):
    """Client for course-member-gradings endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-member-gradings",
            response_model=CourseMemberGradingsGet,
            query_model=CourseMemberGradingsQuery,
        )
