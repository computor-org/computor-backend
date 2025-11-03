"""Auto-generated client for StudentProfileInterface."""

from typing import Optional, List
import httpx

from computor_types.student_profile import (
    StudentProfileCreate,
    StudentProfileGet,
    StudentProfileQuery,
    StudentProfileUpdate,
)
from computor_client.base import BaseEndpointClient


class StudentProfileClient(BaseEndpointClient):
    """Client for student-profiles endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/student-profiles",
            response_model=StudentProfileGet,
            create_model=StudentProfileCreate,
            update_model=StudentProfileUpdate,
            query_model=StudentProfileQuery,
        )
