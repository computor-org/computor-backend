"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.student_course_contents import (
    CourseContentStudentGet,
    CourseContentStudentList,
)
from computor_types.student_courses import (
    CourseStudentGet,
    CourseStudentList,
)

from computor_client.http import AsyncHTTPClient


class StudentsClient:
    """
    Client for students endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def course_contents(
        self,
        course_content_id: str,
        **kwargs: Any,
    ) -> CourseContentStudentGet:
        """Student Get Course Content Endpoint"""
        response = await self._http.get(f"/students/course-contents/{course_content_id}", params=kwargs)
        return CourseContentStudentGet.model_validate(response.json())

    async def get_course_contents(
        self,
        **kwargs: Any,
    ) -> List[CourseContentStudentList]:
        """Student List Course Contents Endpoint"""
        response = await self._http.get(f"/students/course-contents", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseContentStudentList.model_validate(item) for item in data]
        return []

    async def courses(
        self,
        **kwargs: Any,
    ) -> List[CourseStudentList]:
        """Student List Courses Endpoint"""
        response = await self._http.get(f"/students/courses", params=kwargs)
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
        response = await self._http.get(f"/students/courses/{course_id}", params=kwargs)
        return CourseStudentGet.model_validate(response.json())

