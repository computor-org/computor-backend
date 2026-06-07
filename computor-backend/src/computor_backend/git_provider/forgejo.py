import logging
import httpx
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

_BASE = "/api/v1"


class ForgejoProviderClient:
    """
    Forgejo implementation of the git provider Protocol.

    Hierarchy mapping (Option A):
      computor Organization  → Forgejo Organization
      computor CourseFamily  → Forgejo Team  "{family_slug}"  within the org
      computor Course        → Forgejo Team  "{family_slug}/{course_slug}"  within the org
                               + repos named "{family_slug}--{course_slug}--{purpose}"
    """

    def __init__(self, url: str, token: str):
        self._url = url.rstrip("/")
        self._token = token

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._url,
            headers={"Authorization": f"token {self._token}"},
            timeout=30.0,
        )

    # ------------------------------------------------------------------ helpers

    def _org_name(self, org: Organization) -> str:
        return str(org.path).replace(".", "-")

    def _team_name(self, *slugs: str) -> str:
        return "/".join(slugs)

    def _repo_name(self, *slugs: str) -> str:
        return "--".join(slugs)

    def _get_or_create_org(self, client: httpx.Client, name: str, description: str) -> dict:
        r = client.get(f"{_BASE}/orgs/{name}")
        if r.status_code == 200:
            return r.json()
        payload = {
            "username": name,
            "visibility": "private",
            "description": description,
        }
        r = client.post(f"{_BASE}/orgs", json=payload)
        r.raise_for_status()
        return r.json()

    def _get_or_create_team(self, client: httpx.Client, org_name: str, team_name: str, description: str = "") -> dict:
        r = client.get(f"{_BASE}/orgs/{org_name}/teams")
        r.raise_for_status()
        for team in r.json():
            if team["name"] == team_name:
                return team
        payload = {
            "name": team_name,
            "description": description,
            "permission": "write",
            "units": ["repo.code", "repo.issues", "repo.pulls"],
        }
        r = client.post(f"{_BASE}/orgs/{org_name}/teams", json=payload)
        r.raise_for_status()
        return r.json()

    def _get_or_create_repo(self, client: httpx.Client, org_name: str, repo_name: str, description: str = "") -> dict:
        r = client.get(f"{_BASE}/repos/{org_name}/{repo_name}")
        if r.status_code == 200:
            return r.json()
        payload = {
            "name": repo_name,
            "description": description,
            "private": True,
            "auto_init": True,
            "default_branch": "main",
        }
        r = client.post(f"{_BASE}/orgs/{org_name}/repos", json=payload)
        r.raise_for_status()
        return r.json()

    def _add_repo_to_team(self, client: httpx.Client, team_id: int, org_name: str, repo_name: str) -> None:
        r = client.put(f"{_BASE}/teams/{team_id}/repos/{org_name}/{repo_name}")
        if r.status_code not in (204, 422):
            r.raise_for_status()

    # ------------------------------------------------------------------ Protocol

    def setup_organization(
        self,
        config: OrganizationConfig,
        org: Organization,
        user_id: str,
    ) -> OrgProviderResult:
        org_name = self._org_name(org)
        with self._client() as client:
            forgejo_org = self._get_or_create_org(client, org_name, config.description or "")
        return OrgProviderResult(
            provider_entity_id=org_name,
            properties={"forgejo": {
                "org_name": org_name,
                "web_url": f"{self._url}/{org_name}",
            }},
        )

    def setup_course_family(
        self,
        config: CourseFamilyConfig,
        org: Organization,
        family: CourseFamily,
        user_id: str,
    ) -> FamilyProviderResult:
        org_name = self._org_name(org)
        family_slug = config.path
        team_name = self._team_name(family_slug)
        with self._client() as client:
            team = self._get_or_create_team(client, org_name, team_name, config.description or "")
            # Documents repo for the family
            docs_repo = self._get_or_create_repo(
                client, org_name,
                self._repo_name(family_slug, "documents"),
                f"Documents for {config.name}",
            )
            self._add_repo_to_team(client, team["id"], org_name, docs_repo["name"])
        return FamilyProviderResult(
            provider_entity_id=str(team["id"]),
            properties={"forgejo": {
                "org_name": org_name,
                "team_id": team["id"],
                "team_name": team_name,
                "documents_repo": docs_repo["name"],
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
        org_name = self._org_name(org)
        family_slug = (family.properties or {}).get("forgejo", {}).get("team_name", "")
        if not family_slug:
            # fallback: derive from family path
            family_slug = str(family.path).split(".")[-1]
        course_slug = config.path
        team_name = self._team_name(family_slug, course_slug)

        template_repo_name = self._repo_name(family_slug, course_slug, "template")
        assignments_repo_name = self._repo_name(family_slug, course_slug, "assignments")

        with self._client() as client:
            team = self._get_or_create_team(client, org_name, team_name, config.description or "")
            template_repo = self._get_or_create_repo(
                client, org_name, template_repo_name,
                f"Student template for {config.name}",
            )
            assignments_repo = self._get_or_create_repo(
                client, org_name, assignments_repo_name,
                f"Assignments for {config.name}",
            )
            self._add_repo_to_team(client, team["id"], org_name, template_repo["name"])
            self._add_repo_to_team(client, team["id"], org_name, assignments_repo["name"])

        return CourseProviderResult(
            provider_entity_id=str(team["id"]),
            properties={"forgejo": {
                "org_name": org_name,
                "team_id": team["id"],
                "team_name": team_name,
                "template_repo": template_repo["name"],
                "assignments_repo": assignments_repo["name"],
                "template_url": template_repo["html_url"],
                "assignments_url": assignments_repo["html_url"],
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
        org_name = self._org_name(org)
        course_props = (course.properties or {}).get("forgejo", {})
        team_id = course_props.get("team_id")
        template_repo_name = course_props.get("template_repo")

        if not template_repo_name:
            raise ValueError(f"Course {course.id} has no Forgejo template_repo in properties")

        repo_name = username
        with self._client() as client:
            # Fork template repo into the org under the student's username as repo name
            r = client.get(f"{_BASE}/repos/{org_name}/{repo_name}")
            if r.status_code != 200:
                fork_payload = {
                    "organization": org_name,
                    "name": repo_name,
                }
                r = client.post(f"{_BASE}/repos/{org_name}/{template_repo_name}/forks", json=fork_payload)
                r.raise_for_status()
            repo = r.json() if r.status_code == 200 else client.get(f"{_BASE}/repos/{org_name}/{repo_name}").json()

            # Add student as collaborator with write access
            client.put(f"{_BASE}/repos/{org_name}/{repo_name}/collaborators/{username}", json={"permission": "write"})

            if team_id:
                self._add_repo_to_team(client, team_id, org_name, repo_name)

        return StudentRepoResult(
            http_url=repo.get("clone_url", ""),
            ssh_url=repo.get("ssh_url", ""),
            web_url=repo.get("html_url", ""),
            provider_project_id=str(repo.get("id", "")),
            properties={"forgejo": {
                "org_name": org_name,
                "repo_name": repo_name,
                "repo_id": repo.get("id"),
            }},
        )

    def provision_student_fork(
        self,
        template_owner: str,
        template_repo: str,
        target_owner: str,
        new_name: str,
        student_username: str | None = None,
    ) -> StudentRepoResult:
        """Fork ``template_owner/template_repo`` into ``target_owner/new_name``.

        Course-level (binding-driven) replacement for ``create_student_repository``
        — takes explicit refs instead of reading ``course.properties.forgejo``, and
        the caller supplies a collision-free ``new_name`` (fixing the legacy
        bare-username collision). Idempotent: if the target already exists it is
        returned as-is. The student is added as a write collaborator when their
        Forgejo username is known (best-effort — a 404 means they have not logged
        into Forgejo yet, so access is granted on a later retry).
        """
        with self._client() as client:
            existing = client.get(f"{_BASE}/repos/{target_owner}/{new_name}")
            if existing.status_code == 200:
                repo = existing.json()
            else:
                r = client.post(
                    f"{_BASE}/repos/{template_owner}/{template_repo}/forks",
                    json={"organization": target_owner, "name": new_name},
                )
                r.raise_for_status()
                repo = r.json()

            collaborator_added = False
            if student_username:
                cr = client.put(
                    f"{_BASE}/repos/{target_owner}/{new_name}/collaborators/{student_username}",
                    json={"permission": "write"},
                )
                if cr.status_code == 204:
                    collaborator_added = True
                else:
                    logger.warning(
                        "Forgejo: could not add collaborator %s to %s/%s (status %s)",
                        student_username, target_owner, new_name, cr.status_code,
                    )

        return StudentRepoResult(
            http_url=repo.get("clone_url", ""),
            ssh_url=repo.get("ssh_url", ""),
            web_url=repo.get("html_url", ""),
            provider_project_id=str(repo.get("id", "")),
            properties={"forgejo": {
                "owner": target_owner,
                "repo_name": new_name,
                "repo_id": repo.get("id"),
                "collaborator_added": collaborator_added,
            }},
        )

    def sync_member_permissions(
        self,
        org: Organization,
        course: Course,
        username: str,
        role: str,
        user_access_token: str | None,
    ) -> None:
        org_name = self._org_name(org)
        course_props = (course.properties or {}).get("forgejo", {})
        team_id = course_props.get("team_id")

        if not team_id:
            logger.warning(f"No Forgejo team_id on course {course.id}, skipping permission sync")
            return

        with self._client() as client:
            client.put(f"{_BASE}/teams/{team_id}/members/{username}")
