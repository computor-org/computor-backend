"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


from computor_client.http import AsyncHTTPClient


class AnalyticsClient:
    """
    Client for analytics endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def courses(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Analytics Courses"""
        response = await self._http.get(f"/analytics/courses", params=kwargs)
        return response.json()

    async def courses_refresh(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Refresh Course Analytics"""
        response = await self._http.post(f"/analytics/courses/{course_id}/refresh", params=kwargs)
        return response.json()

    async def courses_jobs(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Course Analytics Jobs"""
        response = await self._http.get(f"/analytics/courses/{course_id}/jobs", params=kwargs)
        return response.json()

    async def jobs(
        self,
        job_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Analytics Job"""
        response = await self._http.get(f"/analytics/jobs/{job_id}", params=kwargs)
        return response.json()

    async def courses_summary(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Course Analytics Summary"""
        response = await self._http.get(f"/analytics/courses/{course_id}/summary", params=kwargs)
        return response.json()

    async def courses_students(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Course Analytics Students"""
        response = await self._http.get(f"/analytics/courses/{course_id}/students", params=kwargs)
        return response.json()

    async def get_courses_students(
        self,
        course_id: str,
        course_member_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Course Analytics Student Report"""
        response = await self._http.get(f"/analytics/courses/{course_id}/students/{course_member_id}", params=kwargs)
        return response.json()

    async def get_courses_students_timeline(
        self,
        course_id: str,
        course_member_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Course Analytics Student Timeline"""
        response = await self._http.get(f"/analytics/courses/{course_id}/students/{course_member_id}/timeline", params=kwargs)
        return response.json()

    async def get_courses_students_examples(
        self,
        course_id: str,
        course_member_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Course Analytics Student Examples"""
        response = await self._http.get(f"/analytics/courses/{course_id}/students/{course_member_id}/examples", params=kwargs)
        return response.json()

    async def get_courses_examples_source(
        self,
        course_id: str,
        content_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Analytics Example Source"""
        response = await self._http.get(f"/analytics/courses/{course_id}/examples/{content_id}/source", params=kwargs)
        return response.json()

