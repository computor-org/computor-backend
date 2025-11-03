"""Auto-generated client for CourseContentInterface."""

from typing import Optional, List
import httpx

from computor_types.course_contents import (
    CourseContentCreate,
    CourseContentGet,
    CourseContentQuery,
    CourseContentUpdate,
)
from computor_client.base import BaseEndpointClient


class CourseContentClient(BaseEndpointClient):
    """Client for course-contents endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-contents",
            response_model=CourseContentGet,
            create_model=CourseContentCreate,
            update_model=CourseContentUpdate,
            query_model=CourseContentQuery,
        )
