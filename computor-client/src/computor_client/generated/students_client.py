"""Auto-generated client for /students endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.student_course_contents import (
    CourseContentStudentGet,
    CourseContentStudentList,
)
from computor_types.student_courses import (
    CourseStudentGet,
    CourseStudentList,
)

from computor_client.base import RoleBasedViewClient


class StudentsClient(RoleBasedViewClient):
    """Client for /students endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/students",
        )

    async def get_student_course_content_by_course_content_id(self, course_content_id: str, user_id: Optional[str] = None) -> CourseContentStudentGet:
        """Student Get Course Content Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/course-contents/{course_content_id}", params=params)
        if data:
            return CourseContentStudentGet.model_validate(data)
        return data

    async def get_students_course_contents(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, path: Optional[str] = None, course_id: Optional[str] = None, course_content_type_id: Optional[str] = None, directory: Optional[str] = None, project: Optional[str] = None, provider_url: Optional[str] = None, nlevel: Optional[str] = None, descendants: Optional[str] = None, ascendants: Optional[str] = None, user_id: Optional[str] = None) -> List[CourseContentStudentList]:
        """Student List Course Contents Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'path', 'course_id', 'course_content_type_id', 'directory', 'project', 'provider_url', 'nlevel', 'descendants', 'ascendants', 'user_id'] and v is not None}
        data = await self._request("GET", "/course-contents", params=params)
        if isinstance(data, list):
            return [CourseContentStudentList.model_validate(item) for item in data]
        return data

    async def get_students_courses(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None, path: Optional[str] = None, course_family_id: Optional[str] = None, organization_id: Optional[str] = None, provider_url: Optional[str] = None, full_path: Optional[str] = None, full_path_student: Optional[str] = None, user_id: Optional[str] = None) -> List[CourseStudentList]:
        """Student List Courses Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'description', 'path', 'course_family_id', 'organization_id', 'provider_url', 'full_path', 'full_path_student', 'user_id'] and v is not None}
        data = await self._request("GET", "/courses", params=params)
        if isinstance(data, list):
            return [CourseStudentList.model_validate(item) for item in data]
        return data

    async def get_student_cours_by_course_id(self, course_id: str, user_id: Optional[str] = None) -> CourseStudentGet:
        """Student Get Course Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/courses/{course_id}", params=params)
        if data:
            return CourseStudentGet.model_validate(data)
        return data
