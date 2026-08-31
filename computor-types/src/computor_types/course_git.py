"""Client-facing DTOs for the course-level git descriptor.

Returned by ``GET /user/courses/{course_id}/git`` so a client (the VSCode
extension) can decide how a student obtains their repository for a course:
which delivery mode and student-repo backends the course offers, and where
the ``student-template`` lives. See COURSE_LEVEL_GIT_REFACTOR.md /
VSCODE_STUDENT_REPO_PROVISIONING.md.

Plain response models (not registered CRUD entities).
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

_VALID_STUDENT_REPO_MODES = {"managed", "external", "download"}


class GitTemplateRef(BaseModel):
    """Where the course's ``student-template`` lives, so a client can fork or
    clone it."""

    server_type: str = Field(..., description="Git server type: 'forgejo' | 'gitlab'")
    base_url: str = Field(..., description="Base URL of the git server instance")
    repo: Optional[str] = Field(None, description="Repo/project reference of the template on the server")
    clone_url: Optional[str] = Field(None, description="Clone/web URL of the template")
    default_branch: str = Field("main", description="Default branch of the template")


class CourseGitDescriptor(BaseModel):
    """How a student gets their repository for a course.

    ``configured`` is False when the course has no git binding yet (the client
    should treat the course as not-yet-git-enabled rather than erroring).
    """

    course_id: str
    configured: bool = Field(..., description="Whether the course has a git binding")
    delivery: Optional[str] = Field(None, description="Assignment delivery: 'git' | 'download'")
    student_repo_modes: List[str] = Field(
        default_factory=list,
        description="Allowed student-repo hosting modes, e.g. ['managed', 'external', 'download']",
    )
    template: Optional[GitTemplateRef] = Field(
        None, description="Template location (absent for pure download or unconfigured courses)"
    )


class CourseGitBindingUpsert(BaseModel):
    """Lecturer-facing payload to set/replace a course's git binding."""

    delivery: Literal['git', 'download'] = 'git'
    git_server_id: Optional[str] = Field(None, description="Registry server hosting the student-template")
    parent_group_id: Optional[str] = Field(
        None,
        description="GitLab parent group id/path the course group is created under (GitLab only)",
    )
    token: Optional[str] = Field(
        None,
        description="GitLab group access token bound to this course (GitLab only; stored encrypted, never returned)",
    )
    template_repo: Optional[str] = Field(None, description="Repo/project reference of the student-template")
    template_url: Optional[str] = Field(None, description="Clone/web URL of the student-template")
    default_branch: Optional[str] = Field(None, description="Default branch (defaults to 'main')")
    student_repo_modes: List[str] = Field(
        default_factory=list,
        description="Allowed student-repo hosting modes: subset of ['managed', 'external', 'download']",
    )

    @field_validator("student_repo_modes")
    @classmethod
    def _validate_modes(cls, v: List[str]) -> List[str]:
        bad = [m for m in (v or []) if m not in _VALID_STUDENT_REPO_MODES]
        if bad:
            raise ValueError(
                f"invalid student_repo_modes {bad}; allowed: {sorted(_VALID_STUDENT_REPO_MODES)}"
            )
        return v


class CourseGitBindingGet(BaseModel):
    """Lecturer-facing view of a course's git binding (full config)."""

    id: str
    course_id: str
    delivery: str
    git_server_id: Optional[str] = None
    parent_group_id: Optional[str] = Field(None, description="GitLab parent group id/path (GitLab only)")
    has_token: bool = Field(
        False,
        description="Whether a per-course git token is stored on the binding (the token itself is never returned)",
    )
    template_repo: Optional[str] = None
    template_url: Optional[str] = None
    web_url: Optional[str] = Field(
        None,
        description="Browser-audience URL of the template repository (no .git suffix), "
        "always on the public git host. template_url stays the clone URL for the "
        "requesting audience (a workspace gets its internal host there), so anything "
        "that opens a browser tab must use web_url instead.",
    )
    default_branch: Optional[str] = None
    student_repo_modes: List[str] = Field(default_factory=list)
    locked: bool = Field(
        False,
        description="True once the binding has materialized a template or student repos; "
        "its identity is then immutable (changing it would orphan student repositories).",
    )
    lock_reason: Optional[str] = Field(
        None, description="Human-readable reason the binding is locked, when locked."
    )


class PersonalCloneCredentialGet(BaseModel):
    """A clone credential for working OUTSIDE the managed workspace.

    Deliberately a different Forgejo token than the one the workspace manages
    (rotation is keyed by token name): a workspace credential repair re-mints
    its own token and would silently invalidate anything a student copied off
    the course page (#342). This one is minted once and only re-minted when
    the caller explicitly asks to rotate it.
    """

    clone_username: Optional[str] = None
    clone_token: Optional[str] = Field(
        None,
        description="Repo-scoped personal token — treat it like a password. "
        "Null when the student has no Forgejo identity yet.",
    )
    http_url: Optional[str] = Field(
        None, description="Public HTTPS clone URL of the student's repository."
    )
    clone_command: Optional[str] = Field(
        None,
        description="Complete `git clone` command with the credential embedded, "
        "ready to paste into a terminal.",
    )


class CourseMemberRepositoryGet(BaseModel):
    """A student's repository for a course (the result of provisioning, or the
    recorded BYO location). Tracking only — never read for grading."""

    id: str
    course_member_id: str
    mode: str = Field(..., description="managed | external | download")
    provider_type: Optional[str] = Field(
        None, description="Git server type backing this repo: 'forgejo' | 'gitlab' (null for external/unknown)"
    )
    server_url: Optional[str] = None
    repo_ref: Optional[str] = None
    http_url: Optional[str] = None
    ssh_url: Optional[str] = None
    web_url: Optional[str] = None


class StudentRepositoryProvisioned(CourseMemberRepositoryGet):
    """Provisioning result — the repo plus its clone credential.

    Returned only by `provision-repository`, never by `GET .../repository`.
    `clone_token` is a repo-scoped Forgejo PAT, minted on the first call and
    returned unchanged afterwards — Forgejo keeps one token per user and
    instance, so re-minting would invalidate the copy already embedded in the
    student's existing clones. Call with `rotate=true` to force a fresh token
    (and then update every clone's remote). Authenticate git as:
    `https://<clone_username>:<clone_token>@<host>/<owner>/<repo>.git`.
    `clone_token` is null until the student has logged into Forgejo once
    (re-call after their first login to obtain it).
    """

    clone_token: Optional[str] = Field(None, description="Repo-scoped Forgejo PAT; store securely")
    clone_username: Optional[str] = Field(None, description="Forgejo username to pair with clone_token")


class TemplateAccessGet(BaseModel):
    """A **one-time, read-only** credential for the course's student-template.

    Returned only by `POST .../template-access`. Lets any course member fetch
    the template over git (seed an external repo with history, or merge new
    template commits into their repo). `token` is a fresh read-only Forgejo PAT
    minted (and rotated) on each call under its own token name, so it never
    invalidates the provisioning `clone_token`. It is NOT persisted server-side.
    Authenticate git as `https://<username>:<token>@<host>/<template>.git`.
    `token` is null until the student has logged into the git server once
    (re-call after their first login to obtain it).
    """

    server_type: str = Field(..., description="Git server type hosting the template: 'forgejo'")
    clone_url: Optional[str] = Field(None, description="Public clone URL of the template")
    default_branch: str = Field("main", description="Default branch of the template")
    username: Optional[str] = Field(None, description="Git username to pair with token")
    token: Optional[str] = Field(None, description="One-time READ-ONLY PAT for the template; do not persist")


class CourseMemberRepositoryRegister(BaseModel):
    """Client-supplied location of a student's external repository (e.g. a repo on
    any git provider that the VSCode extension seeded from the course template and
    linked back as ``upstream``).

    Tracking only — the backend never reads this repo (grading is API upload).
    """

    mode: Literal['external', 'managed', 'download'] = 'external'
    server_url: Optional[str] = Field(None, description="Base URL of the git instance hosting the repo")
    repo_ref: Optional[str] = Field(None, description="Provider project/repo reference (e.g. group/path or id)")
    http_url: Optional[str] = None
    ssh_url: Optional[str] = None
    web_url: Optional[str] = None

    @model_validator(mode="after")
    def _require_a_location(self):
        if not (self.http_url or self.web_url or self.ssh_url):
            raise ValueError("at least one of http_url / web_url / ssh_url is required")
        return self
