"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, Union

from computor_types.course_git import (
    CourseGitDescriptor,
    CourseMemberRepositoryGet,
    CourseMemberRepositoryRegister,
    PersonalCloneCredentialGet,
    StudentRepositoryProvisioned,
    TemplateAccessGet,
)
from computor_types.course_member_accounts import (
    CourseMemberProviderAccountUpdate,
    CourseMemberReadinessStatus,
    CourseMemberValidationRequest,
)
from computor_types.course_members import CourseMemberGet
from computor_types.users import (
    UserGet,
    UserScopes,
)

from computor_client.http import AsyncHTTPClient
from computor_client.urls import quote_path


class UserClient:
    """
    Client for user endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def get(
        self,
        **kwargs: Any,
    ) -> UserGet:
        """Get Current User Endpoint"""
        response = await self._http.get("/user", params=kwargs)
        return UserGet.model_validate(response.json())

    async def courses_clone_credential(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> PersonalCloneCredentialGet:
        """Personal Clone Credential Endpoint"""
        response = await self._http.post(f"/user/courses/{quote_path(course_id)}/clone-credential", params=kwargs)
        return PersonalCloneCredentialGet.model_validate(response.json())

    async def courses_enroll(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> CourseMemberGet:
        """Enrol yourself as a student in a public course"""
        response = await self._http.post(f"/user/courses/{quote_path(course_id)}/enroll", params=kwargs)
        return CourseMemberGet.model_validate(response.json())

    async def get_courses_git(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> CourseGitDescriptor:
        """Get Course Git Descriptor Endpoint"""
        response = await self._http.get(f"/user/courses/{quote_path(course_id)}/git", params=kwargs)
        return CourseGitDescriptor.model_validate(response.json())

    async def courses_provision_repository(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> StudentRepositoryProvisioned:
        """Provision Student Repository Endpoint"""
        response = await self._http.post(f"/user/courses/{quote_path(course_id)}/provision-repository", params=kwargs)
        return StudentRepositoryProvisioned.model_validate(response.json())

    async def courses_register(
        self,
        course_id: str,
        data: Union[CourseMemberProviderAccountUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseMemberReadinessStatus:
        """Register Current User Course Account"""
        response = await self._http.post(f"/user/courses/{quote_path(course_id)}/register", json_data=data, params=kwargs)
        return CourseMemberReadinessStatus.model_validate(response.json())

    async def courses_register_gitlab(
        self,
        course_id: str,
        data: Union[CourseMemberValidationRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseMemberRepositoryGet:
        """Register Gitlab Managed Endpoint"""
        response = await self._http.post(f"/user/courses/{quote_path(course_id)}/register-gitlab", json_data=data, params=kwargs)
        return CourseMemberRepositoryGet.model_validate(response.json())

    async def courses_register_repository(
        self,
        course_id: str,
        data: Union[CourseMemberRepositoryRegister, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseMemberRepositoryGet:
        """Register Student Repository Endpoint"""
        response = await self._http.post(f"/user/courses/{quote_path(course_id)}/register-repository", json_data=data, params=kwargs)
        return CourseMemberRepositoryGet.model_validate(response.json())

    async def get_courses_repository(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> CourseMemberRepositoryGet:
        """Get Student Repository Endpoint"""
        response = await self._http.get(f"/user/courses/{quote_path(course_id)}/repository", params=kwargs)
        return CourseMemberRepositoryGet.model_validate(response.json())

    async def courses_template_access(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> TemplateAccessGet:
        """Template Access Endpoint"""
        response = await self._http.post(f"/user/courses/{quote_path(course_id)}/template-access", params=kwargs)
        return TemplateAccessGet.model_validate(response.json())

    async def get_courses_template_archive(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Download Template Archive Endpoint"""
        response = await self._http.get(f"/user/courses/{quote_path(course_id)}/template/archive", params=kwargs)
        return response.json()

    async def courses_validate(
        self,
        course_id: str,
        data: Union[CourseMemberValidationRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseMemberReadinessStatus:
        """Validate Current User Course"""
        response = await self._http.post(f"/user/courses/{quote_path(course_id)}/validate", json_data=data, params=kwargs)
        return CourseMemberReadinessStatus.model_validate(response.json())

    async def get_scopes(
        self,
        **kwargs: Any,
    ) -> UserScopes:
        """Get Current User Scopes"""
        response = await self._http.get("/user/scopes", params=kwargs)
        return UserScopes.model_validate(response.json())

    async def list_views(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Course Views For Current User"""
        response = await self._http.get("/user/views", params=kwargs)
        return response.json()

    async def list_views_by_course_id(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Course Views For Current User By Course"""
        response = await self._http.get(f"/user/views/{quote_path(course_id)}", params=kwargs)
        return response.json()

