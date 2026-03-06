"""
Base deployment classes (dependency-free).

Extracted to avoid circular imports between gitlab.py and deployments_refactored.py.
"""

import yaml
from pydantic import BaseModel
from pydantic_yaml import to_yaml_str


class BaseDeployment(BaseModel):
    """Base class for all deployment configurations."""

    def get_deployment(self) -> str:
        """Get YAML representation of the deployment configuration."""
        return to_yaml_str(self, exclude_none=True, exclude_unset=True)

    def write_deployment(self, filename: str) -> None:
        """Write deployment configuration to a YAML file."""
        with open(filename, "w") as file:
            file.write(self.get_deployment())


class DeploymentFactory:
    """Factory for creating deployment configurations from YAML."""

    @staticmethod
    def read_deployment_from_string(classname, yamlstring: str):
        """Create deployment configuration from YAML string."""
        return classname(**yaml.safe_load(yamlstring))

    @staticmethod
    def read_deployment_from_file(classname, filename: str):
        """Create deployment configuration from YAML file."""
        with open(filename, "r") as file:
            if classname is not None:
                return classname(**yaml.safe_load(file))
            else:
                return yaml.safe_load(file)

    @staticmethod
    def read_deployment_from_file_raw(filename: str) -> dict:
        """Read raw YAML data from file."""
        with open(filename, "r") as file:
            return yaml.safe_load(file)
