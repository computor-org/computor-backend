"""Auto-generated client for CourseStudentInterface."""

from typing import Optional, List
import httpx

from computor_types.student_courses import (
    CourseStudentQuery,
)
from computor_client.base import BaseEndpointClient


class CourseStudentClient(BaseEndpointClient):
    """Client for students/courses endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/students/courses",
            response_model=None,
            query_model=CourseStudentQuery,
        )
