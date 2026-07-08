"""
Base deployment classes (dependency-free).

Extracted to avoid circular imports between gitlab.py and deployment_config.py.
The generic YAML read/write plumbing now lives in ``yaml_config``; the classes
here delegate to it so deployment consumers see no behavior change.
"""

from .yaml_config import (
    YamlConfig,
    read_model_from_yaml_file,
    read_model_from_yaml_string,
    read_yaml_file,
)


class BaseDeployment(YamlConfig):
    """Base class for all deployment configurations."""

    def get_deployment(self) -> str:
        """Get YAML representation of the deployment configuration."""
        return self.to_yaml()

    def write_deployment(self, filename: str) -> None:
        """Write deployment configuration to a YAML file."""
        self.write_yaml(filename)


class DeploymentFactory:
    """Factory for creating deployment configurations from YAML."""

    @staticmethod
    def read_deployment_from_string(classname, yamlstring: str):
        """Create deployment configuration from YAML string."""
        return read_model_from_yaml_string(classname, yamlstring)

    @staticmethod
    def read_deployment_from_file(classname, filename: str):
        """Create deployment configuration from YAML file."""
        return read_model_from_yaml_file(classname, filename)

    @staticmethod
    def read_deployment_from_file_raw(filename: str) -> dict:
        """Read raw YAML data from file."""
        return read_yaml_file(filename)
