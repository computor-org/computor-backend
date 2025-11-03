"""Auto-generated client for CourseMemberCommentInterface."""

from typing import Optional, List
import httpx

from computor_types.course_member_comments import (
    CourseMemberCommentCreate,
    CourseMemberCommentGet,
    CourseMemberCommentQuery,
    CourseMemberCommentUpdate,
)
from computor_client.base import BaseEndpointClient


class CourseMemberCommentClient(BaseEndpointClient):
    """Client for course-member-comments endpoint."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-member-comments",
            response_model=CourseMemberCommentGet,
            create_model=CourseMemberCommentCreate,
            update_model=CourseMemberCommentUpdate,
            query_model=CourseMemberCommentQuery,
        )
