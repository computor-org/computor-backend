import logging
import secrets
import httpx
from computor_types.git_provider import (
    OrgProviderResult,
    FamilyProviderResult,
    CourseProviderResult,
    StudentRepoResult,
)
from computor_types.deployment_config import OrganizationConfig, CourseFamilyConfig, CourseConfig
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
        assignments_repo_name = self._repo_name(family_slug, course_slug, "reference")

        with self._client() as client:
            team = self._get_or_create_team(client, org_name, team_name, config.description or "")
            template_repo = self._get_or_create_repo(
                client, org_name, template_repo_name,
                f"Student template for {config.name}",
            )
            assignments_repo = self._get_or_create_repo(
                client, org_name, assignments_repo_name,
                f"Reference content for {config.name}",
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

        collaborator_added = (
            self.ensure_collaborator(target_owner, new_name, student_username)
            if student_username
            else False
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

    def ensure_collaborator(
        self, owner: str, repo: str, username: str, permission: str = "write"
    ) -> bool:
        """Idempotently grant a user collaborator access on a repo.

        Returns True on success; False (logged) if the user does not exist in
        Forgejo yet — e.g. they have not completed their first OIDC login — so
        the caller can retry on a later provision (self-healing).
        """
        with self._client() as client:
            r = client.put(
                f"{_BASE}/repos/{owner}/{repo}/collaborators/{username}",
                json={"permission": permission},
            )
        if r.status_code == 204:
            return True
        logger.warning(
            "Forgejo: could not add collaborator %s to %s/%s (status %s)",
            username, owner, repo, r.status_code,
        )
        return False

    def mint_user_clone_token(
        self,
        username: str,
        admin_username: str,
        admin_password: str,
        name: str = "computor-vscode",
    ) -> str | None:
        """Mint a repo-scoped personal access token for ``username`` so they can
        clone/push their repo over HTTP.

        Token creation requires **basic auth** (a token cannot create another
        token), so the caller passes the managed instance's admin credentials.
        Rotates: deletes any same-named token first, so every call returns a
        fresh, usable token. Returns the token (shown once) or ``None`` on
        failure — e.g. the student has not completed their first Forgejo login
        yet, so a later retry will succeed.
        """
        auth = (admin_username, admin_password)
        with httpx.Client(base_url=self._url, auth=auth, timeout=30.0) as client:
            # Rotate: a name collision would otherwise 400, and the old secret
            # is unrecoverable, so drop it first (ignore 404).
            client.delete(f"{_BASE}/users/{username}/tokens/{name}")
            r = client.post(
                f"{_BASE}/users/{username}/tokens",
                json={"name": name, "scopes": ["read:repository", "write:repository"]},
            )
        if r.status_code in (200, 201):
            return r.json().get("sha1")
        logger.warning(
            "Forgejo: could not mint clone token for %s (status %s)", username, r.status_code
        )
        return None

    def mint_admin_service_token(
        self,
        admin_username: str,
        admin_password: str,
        name: str = "computor-service",
    ) -> str | None:
        """Mint a rotating service token for the admin user via **basic auth**.

        The course-level registry stores a service token per managed server which
        the backend uses to create orgs/repos and fork student templates — but a
        token cannot create a token, so seeding one requires the admin's basic-auth
        credentials. Scoped to org + repo + user operations. Rotates (drops any
        same-named token first, whose secret is unrecoverable). Returns the token
        (shown once) or ``None`` on failure — e.g. Forgejo not up yet.
        """
        auth = (admin_username, admin_password)
        with httpx.Client(base_url=self._url, auth=auth, timeout=30.0) as client:
            client.delete(f"{_BASE}/users/{admin_username}/tokens/{name}")
            r = client.post(
                f"{_BASE}/users/{admin_username}/tokens",
                json={
                    "name": name,
                    "scopes": ["write:organization", "write:repository", "write:user"],
                },
            )
        if r.status_code in (200, 201):
            return r.json().get("sha1")
        logger.warning(
            "Forgejo: could not mint admin service token (status %s)", r.status_code
        )
        return None

    def ensure_template_repo(self, owner: str, repo: str) -> dict:
        """Ensure the Forgejo org + student-template repo exist (create if
        missing), so a course bound to this managed Forgejo has a real template
        students can fork. Returns the repo dict."""
        with self._client() as client:
            self._get_or_create_org(client, owner, "Computor courses")
            return self._get_or_create_repo(client, owner, repo, "Student template")

    def ensure_reference_repo(self, owner: str, repo: str) -> dict:
        """Ensure the course's reference (solution) repo exists. Created lazily
        and only ever shared with staff (_lecturer+); students never get access.
        Returns the repo dict."""
        with self._client() as client:
            self._get_or_create_org(client, owner, "Computor courses")
            return self._get_or_create_repo(client, owner, repo, "Reference solution")

    def create_course_org(self, name: str) -> str:
        """Try to create a per-course Forgejo org, reporting whether it was new.

        Returns ``"created"`` (HTTP 201) or ``"exists"`` (409/422 — the name is
        already taken). Used to allocate a collision-free org name: the caller
        walks candidate names and takes the first ``"created"``. Forgejo's own
        org-name uniqueness (it rejects a duplicate) serialises concurrent
        allocations, so two different courses can never share an org.
        """
        with self._client() as client:
            r = client.post(
                f"{_BASE}/orgs",
                json={"username": name, "visibility": "private", "description": "Computor course"},
            )
        if r.status_code in (200, 201):
            return "created"
        if r.status_code in (409, 422):
            return "exists"
        r.raise_for_status()
        return "exists"

    # Read-all team that gives _lecturer+ the GitLab "Reporter" equivalent on
    # every repo in a course org (student forks included, now and in future).
    _GRADERS_TEAM = "graders"

    def _ensure_reader_team(self, client: httpx.Client, org_name: str) -> int:
        r = client.get(f"{_BASE}/orgs/{org_name}/teams")
        r.raise_for_status()
        for team in r.json():
            if team["name"] == self._GRADERS_TEAM:
                return team["id"]
        r = client.post(
            f"{_BASE}/orgs/{org_name}/teams",
            json={
                "name": self._GRADERS_TEAM,
                "description": "Lecturers and staff — read access to all course repositories",
                "permission": "read",
                "includes_all_repositories": True,
                "units": ["repo.code", "repo.issues", "repo.pulls"],
            },
        )
        r.raise_for_status()
        return r.json()["id"]

    def grant_org_reader(self, org_name: str, username: str) -> bool:
        """Add ``username`` to the course org's read-all ``graders`` team.

        GitLab "Reporter" equivalent: read on every repo in the org, including
        student forks created *after* the grant (``includes_all_repositories``),
        so a lecturer is added once rather than per-fork. Idempotent; best-effort
        — returns False (logged) if the user has no Forgejo account yet, so a
        later provision self-heals."""
        try:
            with self._client() as client:
                team_id = self._ensure_reader_team(client, org_name)
                r = client.put(f"{_BASE}/teams/{team_id}/members/{username}")
        except httpx.HTTPError as exc:
            logger.warning("Forgejo: could not ensure graders team for %s: %s", org_name, exc)
            return False
        if r.status_code in (200, 204):
            return True
        logger.warning(
            "Forgejo: could not add %s to graders team of %s (status %s)",
            username, org_name, r.status_code,
        )
        return False

    def ensure_user(
        self,
        username: str,
        email: str,
        full_name: str,
        admin_username: str,
        admin_password: str,
    ) -> bool:
        """Idempotently create a local Forgejo account via the admin API so the
        backend can grant repo access (fork collaborator / staff) without waiting
        for the person to log into Forgejo by hand.

        Uses **basic auth** (admin user). The account links to its Keycloak OIDC
        identity on first SSO login — Forgejo is configured with
        ``ACCOUNT_LINKING=auto`` and ``USERNAME=preferred_username`` — so matching
        by ``username`` + ``email`` is the intended, conflict-free flow. A random
        password is set and never used (auth is via SSO). Returns True if the
        account exists (created or already present)."""
        payload = {
            "source_id": 0,
            "login_name": username,
            "username": username,
            "email": email,
            "full_name": full_name or username,
            "password": secrets.token_urlsafe(24),
            "must_change_password": False,
            "send_notify": False,
            "visibility": "private",
        }
        auth = (admin_username, admin_password)
        with httpx.Client(base_url=self._url, auth=auth, timeout=30.0) as client:
            r = client.post(f"{_BASE}/admin/users", json=payload)
        if r.status_code in (200, 201):
            logger.info("Forgejo: created account %s", username)
            return True
        if r.status_code == 422:
            # Already exists (duplicate username/email) — the desired end state.
            return True
        logger.warning(
            "Forgejo: could not ensure account %s (status %s)", username, r.status_code
        )
        return False

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
