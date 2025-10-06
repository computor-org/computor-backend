"""Role-based view clients for students, tutors, and lecturers."""

from typing import Optional, Dict, Any, List
import httpx

from .advanced_base import RoleBasedViewClient


class StudentViewClient(RoleBasedViewClient):
    """Client for student-specific endpoints (/students/*)."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/students",
        )

    async def get_my_courses(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Get courses where I am enrolled as a student.

        Returns:
            List of course views for student role
        """
        return await self.list_courses(params=params)

    async def get_my_course(self, course_id: str) -> Any:
        """
        Get detailed view of a specific course where I am enrolled.

        Args:
            course_id: ID of the course

        Returns:
            Student-specific course view
        """
        return await self.get_course(course_id)

    async def get_my_course_contents(
        self,
        course_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Get course contents available to me as a student.

        Args:
            course_id: Optional course ID to filter by
            params: Additional query parameters

        Returns:
            List of course content views for student
        """
        if course_id:
            params = params or {}
            params['course_id'] = course_id
        return await self.list_course_contents(params=params)

    async def get_course_content_detail(self, course_content_id: str) -> Any:
        """
        Get detailed view of specific course content.

        Args:
            course_content_id: ID of the course content

        Returns:
            Student-specific course content view
        """
        return await self.get_course_content(course_content_id)


class TutorViewClient(RoleBasedViewClient):
    """Client for tutor-specific endpoints (/tutors/*)."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/tutors",
        )

    async def get_my_courses(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Get courses where I am assigned as a tutor.

        Returns:
            List of course views for tutor role
        """
        return await self.list_courses(params=params)

    async def get_my_course(self, course_id: str) -> Any:
        """
        Get detailed view of a specific course where I am a tutor.

        Args:
            course_id: ID of the course

        Returns:
            Tutor-specific course view with student management capabilities
        """
        return await self.get_course(course_id)

    async def get_course_members(
        self,
        course_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Get course members that I can manage as a tutor.

        Args:
            course_id: Optional course ID to filter by
            params: Additional query parameters

        Returns:
            List of course members
        """
        if course_id:
            params = params or {}
            params['course_id'] = course_id
        return await self.custom_get("course-members", params=params)

    async def get_course_member(self, course_member_id: str) -> Any:
        """
        Get detailed view of a specific course member.

        Args:
            course_member_id: ID of the course member

        Returns:
            Course member details
        """
        return await self.custom_get(f"course-members/{course_member_id}")

    async def get_student_course_contents(
        self,
        course_member_id: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Get course contents for a specific student I'm tutoring.

        Args:
            course_member_id: ID of the course member (student)
            params: Additional query parameters

        Returns:
            List of course contents for the student
        """
        return await self.custom_get(
            f"course-members/{course_member_id}/course-contents",
            params=params
        )

    async def get_student_course_content(
        self,
        course_member_id: str,
        course_content_id: str
    ) -> Any:
        """
        Get specific course content for a student I'm tutoring.

        Args:
            course_member_id: ID of the course member (student)
            course_content_id: ID of the course content

        Returns:
            Course content view for the student
        """
        return await self.custom_get(
            f"course-members/{course_member_id}/course-contents/{course_content_id}"
        )

    async def update_student_grades(
        self,
        course_member_id: str,
        course_content_id: str,
        grades_data: Dict[str, Any]
    ) -> Any:
        """
        Update grades for a student's course content.

        Args:
            course_member_id: ID of the course member (student)
            course_content_id: ID of the course content
            grades_data: Grade information to update

        Returns:
            Updated course content with grades
        """
        return await self.custom_patch(
            f"course-members/{course_member_id}/course-contents/{course_content_id}",
            grades_data
        )


class LecturerViewClient(RoleBasedViewClient):
    """Client for lecturer-specific endpoints (/lecturers/*)."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/lecturers",
        )

    async def get_my_courses(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Get courses where I am the lecturer.

        Returns:
            List of course views for lecturer role
        """
        return await self.list_courses(params=params)

    async def get_my_course(self, course_id: str) -> Any:
        """
        Get detailed view of a specific course where I am the lecturer.

        Args:
            course_id: ID of the course

        Returns:
            Lecturer-specific course view with full management capabilities
        """
        return await self.get_course(course_id)

    async def get_my_course_contents(
        self,
        course_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Get course contents for courses I teach.

        Args:
            course_id: Optional course ID to filter by
            params: Additional query parameters

        Returns:
            List of course content views for lecturer
        """
        if course_id:
            params = params or {}
            params['course_id'] = course_id
        return await self.list_course_contents(params=params)

    async def get_course_content_detail(self, course_content_id: str) -> Any:
        """
        Get detailed view of specific course content I manage.

        Args:
            course_content_id: ID of the course content

        Returns:
            Lecturer-specific course content view
        """
        return await self.get_course_content(course_content_id)

    async def create_course_content(
        self,
        course_id: str,
        content_data: Dict[str, Any]
    ) -> Any:
        """
        Create new course content for my course.

        Args:
            course_id: ID of the course
            content_data: Course content information

        Returns:
            Created course content
        """
        return await self.custom_post(
            f"courses/{course_id}/course-contents",
            content_data
        )

    async def update_course_content(
        self,
        course_content_id: str,
        content_data: Dict[str, Any]
    ) -> Any:
        """
        Update course content I manage.

        Args:
            course_content_id: ID of the course content
            content_data: Updated course content information

        Returns:
            Updated course content
        """
        return await self.custom_patch(
            f"course-contents/{course_content_id}",
            content_data
        )

    async def delete_course_content(self, course_content_id: str) -> None:
        """
        Delete course content I manage.

        Args:
            course_content_id: ID of the course content
        """
        await self.custom_delete(f"course-contents/{course_content_id}")
