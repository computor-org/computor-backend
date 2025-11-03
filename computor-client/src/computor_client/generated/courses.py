"""Auto-generated client for CourseInterface."""

from typing import Optional, List
import httpx

from computor_types.courses import (
    CourseCreate,
    CourseGet,
    CourseQuery,
    CourseUpdate,
)
from computor_client.base import BaseEndpointClient


class CourseClient(BaseEndpointClient):
    """Client for courses endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/courses",
            response_model=CourseGet,
            create_model=CourseCreate,
            update_model=CourseUpdate,
            query_model=CourseQuery,
        )
