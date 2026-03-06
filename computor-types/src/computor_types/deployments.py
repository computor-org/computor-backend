"""
Flat deployment configuration models.

Used by temporal workflows, gitlab_builder, and CLI for
organization -> course family -> course creation.

For the newer hierarchical deployment configs, see deployments_refactored.py.
"""

from typing import List, Optional
from pydantic import ConfigDict, Field

# BaseDeployment and DeploymentFactory: canonical in deployments_refactored.py
from computor_types.deployments_refactored import BaseDeployment, DeploymentFactory  # noqa: F401

# GitLab configs + RepositoryConfig: canonical in gitlab.py, re-exported here for backward compat
from computor_types.gitlab import RepositoryConfig, GitLabConfigGet, GitLabConfig  # noqa: F401


class CourseExecutionBackendConfig(BaseDeployment):
    slug: str
    settings: Optional[dict] = None


class FileSourceConfig(BaseDeployment):
    url: str
    token: Optional[str] = None


class CourseSettingsConfig(BaseDeployment):
    model_config = ConfigDict(extra='allow')
    source: Optional[FileSourceConfig] = None


class CourseConfig(BaseDeployment):
    name: str
    path: str
    description: Optional[str] = None
    executionBackends: Optional[List[CourseExecutionBackendConfig]] = None
    settings: Optional[CourseSettingsConfig] = None


class CourseFamilyConfig(BaseDeployment):
    name: str
    path: str
    description: Optional[str] = None
    settings: Optional[dict] = None


class OrganizationConfig(BaseDeployment):
    name: str
    path: str
    description: Optional[str] = None
    settings: Optional[dict] = None
    gitlab: Optional[GitLabConfig] = None


class ComputorDeploymentConfig(BaseDeployment):
    organization: OrganizationConfig
    courseFamily: CourseFamilyConfig
    course: CourseConfig
    settings: Optional[dict] = None


COURSE_DEFAULT_DEPLOYMENT = ComputorDeploymentConfig(
    organization=OrganizationConfig(
        path="computor",
        name="Computor Playground",
        gitlab=GitLabConfig(
            url="https://gitlab.com",
            token="-",
            parent=0
        ),
    ),
    courseFamily=CourseFamilyConfig(
        path="progphys",
        name="Programmieren in der Physik",
    ),
    course=CourseConfig(
        path="2026.python",
        name="Python",
        executionBackends=[
            CourseExecutionBackendConfig(
                slug="itp-python"
            )],
        settings=CourseSettingsConfig(
            source=FileSourceConfig(
                url="https://gitlab.com/../../assignments.git",
                token="-"
            )
        )
    )
)
