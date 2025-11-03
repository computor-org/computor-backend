"""Auto-generated client for CourseContentStudentInterface."""

from typing import Optional, List
import httpx

from computor_types.student_course_contents import (
    CourseContentStudentGet,
    CourseContentStudentQuery,
    CourseContentStudentUpdate,
)
from computor_client.base import BaseEndpointClient


class CourseContentStudentClient(BaseEndpointClient):
    """Client for students/course-contents endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/students/course-contents",
            response_model=CourseContentStudentGet,
            update_model=CourseContentStudentUpdate,
            query_model=CourseContentStudentQuery,
        )
