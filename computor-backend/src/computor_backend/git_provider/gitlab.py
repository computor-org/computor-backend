import logging
from sqlalchemy.orm import Session
from computor_types.git_provider import (
    OrgProviderResult,
    FamilyProviderResult,
    CourseProviderResult,
    StudentRepoResult,
)
from computor_types.deployments_refactored import OrganizationConfig, CourseFamilyConfig, CourseConfig
from ..model.organization import Organization
from ..model.course import CourseFamily, Course

logger = logging.getLogger(__name__)


class GitLabProviderClient:
    def __init__(self, url: str, token: str, db: Session):
        self._url = url
        self._token = token
        self._db = db

    def _builder(self):
        from ..generator.gitlab_builder import GitLabBuilder
        return GitLabBuilder(self._db, self._url, self._token)

    def setup_organization(
        self,
        config: OrganizationConfig,
        org: Organization,
        user_id: str,
    ) -> OrgProviderResult:
        result = self._builder()._create_organization(config, user_id)
        if not result["success"]:
            raise RuntimeError(f"GitLab org setup failed: {result.get('error')}")
        group = result["gitlab_group"]
        return OrgProviderResult(
            provider_entity_id=str(group.id),
            properties={"gitlab": {
                "group_id": group.id,
                "full_path": group.full_path,
                "web_url": group.web_url,
                "visibility": group.visibility,
            }},
        )

    def setup_course_family(
        self,
        config: CourseFamilyConfig,
        org: Organization,
        family: CourseFamily,
        user_id: str,
    ) -> FamilyProviderResult:
        result = self._builder()._create_course_family(config, org, user_id)
        if not result["success"]:
            raise RuntimeError(f"GitLab course family setup failed: {result.get('error')}")
        group = result["gitlab_group"]
        return FamilyProviderResult(
            provider_entity_id=str(group.id),
            properties={"gitlab": {
                "group_id": group.id,
                "full_path": group.full_path,
                "web_url": group.web_url,
            }},
        )

    def setup_course(
        self,
        config: CourseConfig,
        org: Organization,
        family: CourseFamily,
        course: Course,
        user_id: str,
    ) -> CourseProviderResult:
        result = self._builder()._create_course(config, org, family, user_id)
        if not result["success"]:
            raise RuntimeError(f"GitLab course setup failed: {result.get('error')}")
        group = result["gitlab_group"]
        return CourseProviderResult(
            provider_entity_id=str(group.id),
            properties={"gitlab": {
                "group_id": group.id,
                "full_path": group.full_path,
                "web_url": group.web_url,
            }},
        )

    def create_student_repository(
        self,
        course_member_id: str,
        org: Organization,
        course: Course,
        username: str,
        submission_group_ids: list,
    ) -> StudentRepoResult:
        raise NotImplementedError("Use temporal_student_repository directly for now")

    def sync_member_permissions(
        self,
        org: Organization,
        course: Course,
        username: str,
        role: str,
        user_access_token: str | None,
    ) -> None:
        raise NotImplementedError("Use lecturer_gitlab_sync directly for now")
