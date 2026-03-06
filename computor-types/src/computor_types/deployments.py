"""
Legacy deployment configuration models.

This module contains the original (flat) deployment configuration models
still used by temporal workflows, gitlab_builder, and CLI.

For the newer hierarchical deployment configs, see deployments_refactored.py.

Note: CodeAbility test/report/meta models that were previously here have been
moved to their proper modules:
  - testing.py / testing_report.py  (test spec + report models)
  - codeability_meta.py             (meta.yaml models)
"""

import yaml
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic_yaml import to_yaml_str


class DeploymentFactory:

    @staticmethod
    def read_deployment_from_string(classname, yamlstring: str):
        return classname(**yaml.safe_load(yamlstring))

    @staticmethod
    def read_deployment_from_file(classname, filename: str):
        with open(filename, "r") as file:
            if classname is not None:
                return classname(**yaml.safe_load(file))
            else:
                return yaml.safe_load(file)

    @staticmethod
    def read_deployment_from_file_raw(filename: str):
        with open(filename, "r") as file:
            return yaml.safe_load(file)


class BaseDeployment(BaseModel):

    def get_deployment(self):
        return to_yaml_str(self, exclude_none=True, exclude_unset=True)

    def write_deployment(self, filename: str):
        with open(filename, "w") as file:
            file.write(self.get_deployment())


class RepositoryConfig(BaseDeployment):
    settings: Optional[dict] = Field(default_factory=dict)


# GitLab configs: canonical definitions in gitlab.py, re-exported here for backward compat
from computor_types.gitlab import GitLabConfigGet, GitLabConfig  # noqa: E402


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
