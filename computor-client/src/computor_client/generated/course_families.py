"""Auto-generated client for CourseFamilyInterface."""

from typing import Optional, List
import httpx

from computor_types.course_families import (
    CourseFamilyCreate,
    CourseFamilyGet,
    CourseFamilyQuery,
    CourseFamilyUpdate,
)
from computor_client.base import BaseEndpointClient


class CourseFamilyClient(BaseEndpointClient):
    """Client for course-families endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-families",
            response_model=CourseFamilyGet,
            create_model=CourseFamilyCreate,
            update_model=CourseFamilyUpdate,
            query_model=CourseFamilyQuery,
        )
