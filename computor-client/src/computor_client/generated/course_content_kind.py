"""Auto-generated client for CourseContentKindInterface."""

from typing import Optional, List
import httpx

from computor_types.course_content_kind import (
    CourseContentKindCreate,
    CourseContentKindGet,
    CourseContentKindQuery,
    CourseContentKindUpdate,
)
from computor_client.base import BaseEndpointClient


class CourseContentKindClient(BaseEndpointClient):
    """Client for course-content-kinds endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-content-kinds",
            response_model=CourseContentKindGet,
            create_model=CourseContentKindCreate,
            update_model=CourseContentKindUpdate,
            query_model=CourseContentKindQuery,
        )
