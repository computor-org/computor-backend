import logging
import time

from gitlab import Gitlab
from gitlab.exceptions import GitlabCreateError, GitlabGetError
from sqlalchemy.orm import Session
from computor_types.git_provider import (
    OrgProviderResult,
    FamilyProviderResult,
    CourseProviderResult,
    StudentRepoResult,
)
from computor_types.deployment_config import OrganizationConfig, CourseFamilyConfig, CourseConfig
from ..model.organization import Organization
from ..model.course import CourseFamily, Course
from gitlab.exceptions import GitlabHttpError
from ..gitlab_utils import (
    construct_gitlab_http_url,
    construct_gitlab_ssh_url,
    construct_gitlab_web_url,
)

logger = logging.getLogger(__name__)

# GitLab member access levels.
GITLAB_REPORTER = 20
GITLAB_DEVELOPER = 30
GITLAB_MAINTAINER = 40


def make_gitlab_client(url: str, token: str) -> Gitlab:
    """python-gitlab client factory: Docker-aware URL, stable base URL.

    ``keep_base_url=True`` stops python-gitlab from following the instance's
    advertised external URL, which is unreachable from inside containers.
    """
    from ..utils.docker_utils import transform_localhost_url

    return Gitlab(
        url=transform_localhost_url(url),
        private_token=token,
        keep_base_url=True,
    )


def gitlab_unprotect_branches(gitlab: Gitlab, id: str | int, branch_name) -> None:
    """Remove branch protection; a 404 (already unprotected) is fine."""
    try:
        gitlab.http_delete(path=f"/projects/{id}/protected_branches/{branch_name}")
        logger.info("Unprotected branch %s of project %s", branch_name, id)
    except GitlabHttpError as e:
        if e.response_code == 404:
            logger.info("Branch '%s' already unprotected [projectId=%s]", branch_name, id)
        else:
            raise


def gitlab_fork_project(gitlab: Gitlab, fork_id: str | int, dest_path: str, dest_name: str, namespace_id: str | int) -> None:
    """Kick off an async GitLab fork; poll for the result separately."""
    try:
        gitlab.http_post(path=f"/projects/{fork_id}/fork",
              post_data={
                "path": dest_path,
                "name": dest_name,
                "namespace_id": namespace_id
              })
    except Exception as e:
        logger.error("gitlab_fork_project failed: %s", e)
        raise


def fork_project_with_polling(
    gl: Gitlab,
    source_project_id: int | str,
    dest_path: str,
    dest_name: str,
    namespace_id: int | str,
    *,
    max_attempts: int = 30,
    poll_interval: float = 1.0,
    initial_wait: float = 0.0,
    sleep=time.sleep,
):
    """Fork a project and wait until the destination finished importing.

    GitLab forks are asynchronous; this is the single implementation of
    fork-then-poll (callers in async contexts should run it in a thread).
    """
    gitlab_fork_project(gl, source_project_id, dest_path, dest_name, namespace_id)

    if initial_wait:
        sleep(initial_wait)

    namespace_full_path = gl.groups.get(namespace_id).full_path
    ref = f"{namespace_full_path}/{dest_path}"
    last = None
    for _ in range(max_attempts):
        try:
            project = gl.projects.get(ref)
            status = getattr(project, "import_status", "finished")
            if status in (None, "none", "finished"):
                return project
            last = status
        except GitlabGetError:
            last = "404"
        sleep(poll_interval)
    raise RuntimeError(f"GitLab fork {ref} not ready (last status: {last})")


def add_member_idempotent(target, gitlab_user_id: int, access_level: int) -> bool:
    """Add (or raise to) a member on an already-fetched project/group object.

    Never lowers an existing higher access level. Returns True on success.
    """
    try:
        target.members.create({"user_id": gitlab_user_id, "access_level": access_level})
        return True
    except GitlabCreateError as e:
        if getattr(e, "response_code", None) == 409:
            member = target.members.get(gitlab_user_id)
            if member.access_level < access_level:
                member.access_level = access_level
                member.save()
            return True
        logger.warning(
            "GitLab: could not add member %s to %s (%s)", gitlab_user_id, target, e
        )
        return False


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

    # ------------------------------------------------------------------
    # Course-level managed provisioning (GitServer registry + binding).
    #
    # These operate purely on the backend's GROUP access token (``self._token``)
    # and a parent group id — no Organization/CourseFamily rows required, so a
    # course can be provisioned "flat" directly under a registered parent group.
    # A group token can create subgroups/projects, fork, and add members by id;
    # it cannot search users by email (that is resolved from the student's own
    # PAT via ``GET /api/v4/user`` elsewhere) — so this client only ever adds a
    # member once the caller already has the GitLab user id.
    # ------------------------------------------------------------------

    def _gl(self) -> Gitlab:
        """python-gitlab client on the registry's group token (Docker-aware URL)."""
        return make_gitlab_client(self._url, self._token)

    def _get_or_create_subgroup(self, gl, parent_id, path, name, description=""):
        parent = gl.groups.get(parent_id)
        for sg in parent.subgroups.list(search=path, all=True):
            if sg.path == path:
                return gl.groups.get(sg.id)
        return gl.groups.create({
            "name": name,
            "path": path,
            "parent_id": parent.id,
            "visibility": "private",
            "description": description,
        })

    def _find_project_in_namespace(self, gl, namespace_id, path):
        for p in gl.projects.list(search=path, all=True):
            ns = p.namespace.get("id") if hasattr(p.namespace, "get") else p.namespace.id
            if p.path == path and ns == namespace_id:
                return gl.projects.get(p.id)
        return None

    def _get_or_create_project(self, gl, namespace_id, path, name, description=""):
        existing = self._find_project_in_namespace(gl, namespace_id, path)
        if existing is not None:
            return existing
        return gl.projects.create({
            "name": name,
            "path": path,
            "namespace_id": namespace_id,
            "description": description,
            "visibility": "private",
            "initialize_with_readme": True,
            "default_branch": "main",
        })

    def ensure_course_structure(self, parent_group_id, course_slug, course_name=None) -> dict:
        """Idempotently create the flat course structure under ``parent_group_id``:
        a course group containing ``template`` + ``reference`` projects and a
        ``students`` subgroup. Returns the ids/paths to persist on the binding.
        """
        gl = self._gl()
        name = course_name or course_slug
        course_group = self._get_or_create_subgroup(
            gl, parent_group_id, course_slug, name, f"Course {name}"
        )
        template = self._get_or_create_project(
            gl, course_group.id, "template", "Template", f"Student template for {name}"
        )
        reference = self._get_or_create_project(
            gl, course_group.id, "reference", "Reference", f"Reference (full) content for {name}"
        )
        students = self._get_or_create_subgroup(
            gl, course_group.id, "students", "Students", f"Student repositories for {name}"
        )
        return {
            "parent_group_id": parent_group_id,
            "course_group_id": course_group.id,
            "course_group_path": course_group.full_path,
            "template_project_id": template.id,
            "template_path": template.path_with_namespace,
            "template_url": construct_gitlab_http_url(self._url, template.path_with_namespace),
            "reference_project_id": reference.id,
            "reference_path": reference.path_with_namespace,
            "students_group_id": students.id,
            "students_group_path": students.full_path,
        }

    def provision_student_fork(self, template_project_id, students_group_id, new_name, new_path=None) -> StudentRepoResult:
        """Fork the course ``template`` project into the ``students`` subgroup as
        the student's repository. Idempotent (returns the existing fork if present).
        Removes branch protection on main/master so the student can push.
        """
        gl = self._gl()
        dest_path = new_path or new_name
        project = self._find_project_in_namespace(gl, students_group_id, dest_path)
        if project is None:
            project = fork_project_with_polling(
                gl, template_project_id, dest_path, new_name, students_group_id
            )
        for branch in ("main", "master"):
            gitlab_unprotect_branches(gl, project.id, branch)
        full_path = project.path_with_namespace
        return StudentRepoResult(
            http_url=construct_gitlab_http_url(self._url, full_path) or "",
            ssh_url=construct_gitlab_ssh_url(full_path) or "",
            web_url=construct_gitlab_web_url(self._url, full_path) or "",
            provider_project_id=str(project.id),
            properties={"gitlab": {
                "project_id": project.id,
                "namespace_id": students_group_id,
                "full_path": full_path,
            }},
        )

    def add_member(self, target_id, gitlab_user_id, access_level, is_group=False) -> bool:
        """Idempotently add (or raise to) a member on a project/group by GitLab
        user id, using the backend's group token. Returns True on success."""
        gl = self._gl()
        target = gl.groups.get(target_id) if is_group else gl.projects.get(target_id)
        return add_member_idempotent(target, gitlab_user_id, access_level)
