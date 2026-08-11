"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, List

from computor_types.student_course_contents import (
    CourseContentStudentGet,
    CourseContentStudentList,
)
from computor_types.student_courses import (
    CourseStudentGet,
    CourseStudentList,
)

from computor_client.http import AsyncHTTPClient
from computor_client.urls import quote_path


class StudentsClient:
    """
    Client for students endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list_course_contents(
        self,
        **kwargs: Any,
    ) -> List[CourseContentStudentList]:
        """Student List Course Contents Endpoint"""
        response = await self._http.get("/students/course-contents", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseContentStudentList.model_validate(item) for item in data]
        return []

    async def get_course_contents(
        self,
        course_content_id: str,
        **kwargs: Any,
    ) -> CourseContentStudentGet:
        """Student Get Course Content Endpoint"""
        response = await self._http.get(f"/students/course-contents/{quote_path(course_content_id)}", params=kwargs)
        return CourseContentStudentGet.model_validate(response.json())

    async def list_courses(
        self,
        **kwargs: Any,
    ) -> List[CourseStudentList]:
        """Student List Courses Endpoint"""
        response = await self._http.get("/students/courses", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseStudentList.model_validate(item) for item in data]
        return []

    async def get_courses(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> CourseStudentGet:
        """Student Get Course Endpoint"""
        response = await self._http.get(f"/students/courses/{quote_path(course_id)}", params=kwargs)
        return CourseStudentGet.model_validate(response.json())

