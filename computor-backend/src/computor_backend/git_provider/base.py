from typing import Protocol, runtime_checkable
from computor_types.git_provider import (
    OrgProviderResult,
    FamilyProviderResult,
    CourseProviderResult,
    StudentRepoResult,
)
from computor_types.deployments_refactored import OrganizationConfig, CourseFamilyConfig, CourseConfig
from ..model.organization import Organization
from ..model.course import CourseFamily, Course


@runtime_checkable
class GitProviderClient(Protocol):
    def setup_organization(
        self,
        config: OrganizationConfig,
        org: Organization,
        user_id: str,
    ) -> OrgProviderResult: ...

    def setup_course_family(
        self,
        config: CourseFamilyConfig,
        org: Organization,
        family: CourseFamily,
        user_id: str,
    ) -> FamilyProviderResult: ...

    def setup_course(
        self,
        config: CourseConfig,
        org: Organization,
        family: CourseFamily,
        course: Course,
        user_id: str,
    ) -> CourseProviderResult: ...

    def create_student_repository(
        self,
        course_member_id: str,
        org: Organization,
        course: Course,
        username: str,
        submission_group_ids: list,
    ) -> StudentRepoResult: ...

    def sync_member_permissions(
        self,
        org: Organization,
        course: Course,
        username: str,
        role: str,
        user_access_token: str | None,
    ) -> None: ...
