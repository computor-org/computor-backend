"""Auto-generated client for CourseContentTypeInterface."""

from typing import Optional, List
import httpx

from computor_types.course_content_types import (
    CourseContentTypeCreate,
    CourseContentTypeGet,
    CourseContentTypeQuery,
    CourseContentTypeUpdate,
)
from computor_client.base import TypedEndpointClient


class CourseContentTypeClient(TypedEndpointClient):
    """Client for course-content-types endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-content-types",
            response_model=CourseContentTypeGet,
            create_model=CourseContentTypeCreate,
            update_model=CourseContentTypeUpdate,
            query_model=CourseContentTypeQuery,
        )
