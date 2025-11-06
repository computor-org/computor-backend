"""Auto-generated client for CourseRoleInterface."""

from typing import Optional, List
import httpx

from computor_types.course_roles import (
    CourseRoleGet,
    CourseRoleQuery,
)
from computor_client.base import TypedEndpointClient


class CourseRoleClient(TypedEndpointClient):
    """Client for course-roles endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-roles",
            response_model=CourseRoleGet,
            query_model=CourseRoleQuery,
        )
