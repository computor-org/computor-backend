"""
Generic YAML config read/write plumbing (dependency-free).

Provides YAML load/dump helpers decoupled from deployment types, so any
pydantic config model can be serialized to / loaded from a YAML file without
importing deployment DTOs. ``deployment_base.DeploymentFactory`` and
``BaseDeployment`` delegate to these helpers, and lightweight CLI configs
(e.g. ``computor_cli.config.CLIAuthConfig``) can use them directly.
"""

from typing import Any, Optional, Type, TypeVar

import yaml
from pydantic import BaseModel
from pydantic_yaml import to_yaml_str

T = TypeVar("T", bound=BaseModel)


def model_to_yaml_str(model: BaseModel) -> str:
    """Serialize a pydantic model to a YAML string (excluding unset/None)."""
    return to_yaml_str(model, exclude_none=True, exclude_unset=True)


def write_model_to_yaml_file(model: BaseModel, filename: str) -> None:
    """Write a pydantic model to a YAML file."""
    with open(filename, "w") as file:
        file.write(model_to_yaml_str(model))


def read_yaml_file(filename: str) -> Any:
    """Read raw YAML data from a file."""
    with open(filename, "r") as file:
        return yaml.safe_load(file)


def read_model_from_yaml_string(classname: Type[T], yamlstring: str) -> T:
    """Create a pydantic model from a YAML string."""
    return classname(**yaml.safe_load(yamlstring))


def read_model_from_yaml_file(classname: Optional[Type[T]], filename: str):
    """Create a pydantic model from a YAML file.

    If ``classname`` is ``None`` the raw parsed YAML (dict) is returned.
    """
    with open(filename, "r") as file:
        data = yaml.safe_load(file)
    if classname is not None:
        return classname(**data)
    return data


class YamlConfig(BaseModel):
    """Base class for pydantic configs that can be read/written as YAML files."""

    def to_yaml(self) -> str:
        """Get the YAML representation of this config."""
        return model_to_yaml_str(self)

    def write_yaml(self, filename: str) -> None:
        """Write this config to a YAML file."""
        write_model_to_yaml_file(self, filename)
