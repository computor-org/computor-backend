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

from pydantic import BaseModel, Field, field_validator

_VALID_STUDENT_REPO_MODES = {"forgejo", "gitlab_byo", "download"}


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
        description="Allowed student-repo backends, e.g. ['forgejo', 'gitlab_byo', 'download']",
    )
    template: Optional[GitTemplateRef] = Field(
        None, description="Template location (absent for pure download or unconfigured courses)"
    )


class CourseGitBindingUpsert(BaseModel):
    """Lecturer-facing payload to set/replace a course's git binding."""

    delivery: Literal['git', 'download'] = 'git'
    git_server_id: Optional[str] = Field(None, description="Registry server hosting the student-template")
    template_repo: Optional[str] = Field(None, description="Repo/project reference of the student-template")
    template_url: Optional[str] = Field(None, description="Clone/web URL of the student-template")
    default_branch: Optional[str] = Field(None, description="Default branch (defaults to 'main')")
    student_repo_modes: List[str] = Field(
        default_factory=list,
        description="Allowed student-repo backends: subset of ['forgejo', 'gitlab_byo', 'download']",
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
    template_repo: Optional[str] = None
    template_url: Optional[str] = None
    default_branch: Optional[str] = None
    student_repo_modes: List[str] = Field(default_factory=list)


class CourseMemberRepositoryGet(BaseModel):
    """A student's repository for a course (the result of provisioning, or the
    recorded BYO location). Tracking only — never read for grading."""

    id: str
    course_member_id: str
    mode: str = Field(..., description="forgejo | gitlab_byo | download")
    server_url: Optional[str] = None
    repo_ref: Optional[str] = None
    http_url: Optional[str] = None
    ssh_url: Optional[str] = None
    web_url: Optional[str] = None
