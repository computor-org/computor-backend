"""Auto-generated client for /tutors endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.student_course_contents import (
    CourseContentStudentGet,
    CourseContentStudentList,
)
from computor_types.tutor_course_members import (
    TutorCourseMemberGet,
    TutorCourseMemberList,
)
from computor_types.tutor_courses import (
    CourseTutorGet,
    CourseTutorList,
)
from computor_types.tutor_grading import (
    TutorGradeCreate,
    TutorGradeResponse,
)
from computor_types.tutor_submission_groups import (
    TutorSubmissionGroupGet,
    TutorSubmissionGroupList,
)

from computor_client.base import RoleBasedViewClient


class TutorsClient(RoleBasedViewClient):
    """Client for /tutors endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/tutors",
        )

    async def get_tutor_course_member_course_content_by_course_content_id(self, course_member_id: str, course_content_id: str, user_id: Optional[str] = None) -> CourseContentStudentGet:
        """Tutor Get Course Contents Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/course-members/{course_member_id}/course-contents/{course_content_id}", params=params)
        if data:
            return CourseContentStudentGet.model_validate(data)
        return data

    async def patch_tutor_course_member_course_content_by_course_content_id(self, course_member_id: str, course_content_id: str, payload: TutorGradeCreate, user_id: Optional[str] = None) -> TutorGradeResponse:
        """Tutor Update Course Contents Endpoint"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/course-members/{course_member_id}/course-contents/{course_content_id}", json=json_data)
        if data:
            return TutorGradeResponse.model_validate(data)
        return data

    async def get_tutor_course_member_course_content(self, course_member_id: str, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, path: Optional[str] = None, course_id: Optional[str] = None, course_content_type_id: Optional[str] = None, directory: Optional[str] = None, project: Optional[str] = None, provider_url: Optional[str] = None, nlevel: Optional[str] = None, descendants: Optional[str] = None, ascendants: Optional[str] = None, user_id: Optional[str] = None) -> List[CourseContentStudentList]:
        """Tutor List Course Contents Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'path', 'course_id', 'course_content_type_id', 'directory', 'project', 'provider_url', 'nlevel', 'descendants', 'ascendants', 'user_id'] and v is not None}
        data = await self._request("GET", f"/course-members/{course_member_id}/course-contents", params=params)
        if isinstance(data, list):
            return [CourseContentStudentList.model_validate(item) for item in data]
        return data

    async def get_tutor_cours_by_course_id(self, course_id: str, user_id: Optional[str] = None) -> CourseTutorGet:
        """Tutor Get Courses Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/courses/{course_id}", params=params)
        if data:
            return CourseTutorGet.model_validate(data)
        return data

    async def get_tutors_courses(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None, path: Optional[str] = None, course_family_id: Optional[str] = None, organization_id: Optional[str] = None, provider_url: Optional[str] = None, full_path: Optional[str] = None, full_path_student: Optional[str] = None, user_id: Optional[str] = None) -> List[CourseTutorList]:
        """Tutor List Courses Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'description', 'path', 'course_family_id', 'organization_id', 'provider_url', 'full_path', 'full_path_student', 'user_id'] and v is not None}
        data = await self._request("GET", "/courses", params=params)
        if isinstance(data, list):
            return [CourseTutorList.model_validate(item) for item in data]
        return data

    async def get_tutor_course_member_by_course_member_id(self, course_member_id: str, user_id: Optional[str] = None) -> TutorCourseMemberGet:
        """Tutor Get Course Members Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/course-members/{course_member_id}", params=params)
        if data:
            return TutorCourseMemberGet.model_validate(data)
        return data

    async def get_tutors_course_members(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, user_id: Optional[str] = None, course_id: Optional[str] = None, course_group_id: Optional[str] = None, course_role_id: Optional[str] = None, given_name: Optional[str] = None, family_name: Optional[str] = None) -> List[TutorCourseMemberList]:
        """Tutor List Course Members Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'user_id', 'course_id', 'course_group_id', 'course_role_id', 'given_name', 'family_name'] and v is not None}
        data = await self._request("GET", "/course-members", params=params)
        if isinstance(data, list):
            return [TutorCourseMemberList.model_validate(item) for item in data]
        return data

    async def get_tutor_submission_group_by_submission_group_id(self, submission_group_id: str, user_id: Optional[str] = None) -> TutorSubmissionGroupGet:
        """Tutor Get Submission Group Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/submission-groups/{submission_group_id}", params=params)
        if data:
            return TutorSubmissionGroupGet.model_validate(data)
        return data

    async def get_tutors_submission_groups(self, course_id: Optional[str] = None, course_content_id: Optional[str] = None, course_group_id: Optional[str] = None, has_submissions: Optional[str] = None, has_ungraded_submissions: Optional[str] = None, limit: Optional[str] = None, offset: Optional[str] = None, user_id: Optional[str] = None) -> List[TutorSubmissionGroupList]:
        """Tutor List Submission Groups Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['course_id', 'course_content_id', 'course_group_id', 'has_submissions', 'has_ungraded_submissions', 'limit', 'offset', 'user_id'] and v is not None}
        data = await self._request("GET", "/submission-groups", params=params)
        if isinstance(data, list):
            return [TutorSubmissionGroupList.model_validate(item) for item in data]
        return data

    async def get_tutor_course_content_reference(self, course_content_id: str, with_dependencies: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Download Course Content Reference"""
        params = {k: v for k, v in locals().items() if k in ['with_dependencies', 'user_id'] and v is not None}
        data = await self._request("GET", f"/course-contents/{course_content_id}/reference", params=params)
        if data:
            return Dict[str, Any].model_validate(data)
        return data
