"""Auto-generated client for CourseExecutionBackendInterface."""

from typing import Optional, List
import httpx

from computor_types.course_execution_backends import (
    CourseExecutionBackendCreate,
    CourseExecutionBackendGet,
    CourseExecutionBackendQuery,
    CourseExecutionBackendUpdate,
)
from computor_client.base import BaseEndpointClient


class CourseExecutionBackendClient(BaseEndpointClient):
    """Client for course-execution-backends endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-execution-backends",
            response_model=CourseExecutionBackendGet,
            create_model=CourseExecutionBackendCreate,
            update_model=CourseExecutionBackendUpdate,
            query_model=CourseExecutionBackendQuery,
        )
