"""Client-facing DTOs for the course-level git descriptor.

Returned by ``GET /user/courses/{course_id}/git`` so a client (the VSCode
extension) can decide how a student obtains their repository for a course:
which delivery mode and student-repo backends the course offers, and where
the ``student-template`` lives. See COURSE_LEVEL_GIT_REFACTOR.md /
VSCODE_STUDENT_REPO_PROVISIONING.md.

Plain response models (not registered CRUD entities).
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


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
