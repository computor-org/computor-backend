"""Auto-generated client for CourseContentLecturerInterface."""

from typing import Optional, List
import httpx

from computor_types.lecturer_course_contents import (
    CourseContentLecturerGet,
    CourseContentLecturerQuery,
)
from computor_client.base import BaseEndpointClient


class CourseContentLecturerClient(BaseEndpointClient):
    """Client for lecturers/course-contents endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/lecturers/course-contents",
            response_model=CourseContentLecturerGet,
            query_model=CourseContentLecturerQuery,
        )
