"""Auto-generated client for CourseMemberInterface."""

from typing import Optional, List
import httpx

from computor_types.course_members import (
    CourseMemberCreate,
    CourseMemberGet,
    CourseMemberQuery,
    CourseMemberUpdate,
)
from computor_client.base import TypedEndpointClient


class CourseMemberClient(TypedEndpointClient):
    """Client for course-members endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-members",
            response_model=CourseMemberGet,
            create_model=CourseMemberCreate,
            update_model=CourseMemberUpdate,
            query_model=CourseMemberQuery,
        )
