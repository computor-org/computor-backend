"""Auto-generated client for CourseGroupInterface."""

from typing import Optional, List
import httpx

from computor_types.course_groups import (
    CourseGroupCreate,
    CourseGroupGet,
    CourseGroupQuery,
    CourseGroupUpdate,
)
from computor_client.base import TypedEndpointClient


class CourseGroupClient(TypedEndpointClient):
    """Client for course-groups endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-groups",
            response_model=CourseGroupGet,
            create_model=CourseGroupCreate,
            update_model=CourseGroupUpdate,
            query_model=CourseGroupQuery,
        )
