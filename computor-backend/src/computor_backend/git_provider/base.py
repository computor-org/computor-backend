from typing import Protocol, runtime_checkable
from computor_types.git_provider import (
    OrgProviderResult,
    FamilyProviderResult,
    CourseProviderResult,
)
from computor_types.deployment_config import OrganizationConfig, CourseFamilyConfig, CourseConfig
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
