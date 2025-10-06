"""Computor Types - Pydantic DTOs for Computor platform."""

__version__ = "0.1.0"

# Base classes
from .base import (
    EntityInterface,
    BaseEntityGet,
    BaseEntityList,
    ListQuery,
)


def get_all_dtos():
    """
    Get all EntityInterface subclasses registered in this package.

    This is used by the backend for permission setup and other
    discovery mechanisms.

    Returns:
        List of EntityInterface subclasses
    """
    import pkgutil
    import inspect
    import computor_types

    interfaces = []
    seen_names = set()

    for module_info in pkgutil.walk_packages(
        computor_types.__path__,
        computor_types.__name__ + "."
    ):
        try:
            module = __import__(module_info.name, fromlist=["__name__"])

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, EntityInterface) and
                    obj is not EntityInterface and
                    name not in seen_names and
                    name.endswith('Interface')
                ):
                    interfaces.append(obj)
                    seen_names.add(name)
        except Exception:
            # Skip modules that can't be imported
            continue

    return interfaces

# Organizations
from .organizations import (
    OrganizationInterface,
    OrganizationType,
    OrganizationProperties,
    OrganizationPropertiesGet,
    OrganizationCreate,
    OrganizationGet,
    OrganizationList,
    OrganizationUpdate,
    OrganizationQuery,
)

# Course Families
from .course_families import (
    CourseFamilyInterface,
    CourseFamilyCreate,
    CourseFamilyGet,
    CourseFamilyList,
    CourseFamilyUpdate,
    CourseFamilyQuery,
)

# Courses
from .courses import (
    CourseInterface,
    CourseCreate,
    CourseGet,
    CourseList,
    CourseUpdate,
    CourseQuery,
)

# Users
from .users import (
    UserInterface,
    UserCreate,
    UserGet,
    UserList,
    UserUpdate,
    UserQuery,
)

# Auth
from .auth import (
    BasicAuthConfig,
    GLPAuthConfig,
)

# Deployments
from .deployments import (
    GitLabConfig,
    GitLabConfigGet,
    BaseDeployment,
)

__all__ = [
    "EntityInterface",
    "BaseEntityGet",
    "BaseEntityList",
    "ListQuery",
    "OrganizationInterface",
    "OrganizationType",
    "OrganizationCreate",
    "OrganizationGet",
    "CourseFamilyInterface",
    "CourseFamilyCreate",
    "CourseFamilyGet",
    "CourseInterface",
    "CourseCreate",
    "CourseGet",
    "UserInterface",
    "UserCreate",
    "UserGet",
    "BasicAuthConfig",
    "GLPAuthConfig",
    "GitLabConfig",
    "GitLabConfigGet",
    "BaseDeployment",
]
