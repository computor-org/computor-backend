"""Auto-generated client for CourseTutorInterface."""

from typing import Optional, List
import httpx

from computor_types.tutor_courses import (
    CourseTutorQuery,
)
from computor_client.base import BaseEndpointClient


class CourseTutorClient(BaseEndpointClient):
    """Client for tutors/courses endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/tutors/courses",
            response_model=None,
            query_model=CourseTutorQuery,
        )
