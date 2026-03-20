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

# Deployments (imported from dependency-free base to avoid circular imports)
from .deployment_base import BaseDeployment
from .gitlab import GitLabConfig, GitLabConfigGet

# Testing (test.yaml models)
from .testing import (
    ComputorTestSuite,
    ComputorTestCollection,
    ComputorTest,
    ComputorTestProperty,
    ComputorSpecification,
    QualificationEnum,
    TypeEnum,
    StatusEnum,
    ResultEnum,
)

# Testing reports (testSummary.json models)
from .testing_report import (
    ComputorReport,
    ComputorReportMain,
    ComputorReportSub,
    ComputorReportSummary,
)

# Meta.yaml models
from .codeability_meta import (
    CodeAbilityMeta,
    CodeAbilityMetaProperties,
    CodeAbilityPerson,
    CodeAbilityLink,
    CourseExecutionBackendConfig,
    TestDependency,
)

# Exceptions
from .exceptions import (
    VsixManifestError,
)

# Messages
from .messages import (
    MessageTargetProtocol,
)

# WebSocket Events
from .websocket import (
    WSChannelSubscribe,
    WSChannelUnsubscribe,
    WSTypingStart,
    WSTypingStop,
    WSReadMark,
    WSPing,
    WSChannelSubscribed,
    WSChannelUnsubscribed,
    WSChannelError,
    WSMessageNew,
    WSMessageUpdate,
    WSMessageDelete,
    WSTypingUpdate,
    WSReadUpdate,
    WSPong,
    WSError,
    WSConnected,
    WSDeploymentStatusChanged,
    WSDeploymentAssigned,
    WSDeploymentUnassigned,
    WSCourseContentUpdated,
    ClientEvent,
    ServerEvent,
    parse_client_event,
)

# Extensions
from .extensions import (
    VsixMetadata,
    ExtensionInterface,
    ExtensionPublishRequest,
    ExtensionMetadata,
    ExtensionVersionDetail,
)

# Cascade Deletion
from .cascade_deletion import (
    EntityDeleteCount,
    CascadeDeletePreview,
    CascadeDeleteResult,
    ExampleDeletePreview,
    ExampleBulkDeleteRequest,
    ExampleBulkDeleteResult,
)

__all__ = [
    # Base
    "EntityInterface",
    "BaseEntityGet",
    "BaseEntityList",
    "ListQuery",
    # Organizations
    "OrganizationInterface",
    "OrganizationType",
    "OrganizationCreate",
    "OrganizationGet",
    # Course Families
    "CourseFamilyInterface",
    "CourseFamilyCreate",
    "CourseFamilyGet",
    # Courses
    "CourseInterface",
    "CourseCreate",
    "CourseGet",
    # Users
    "UserInterface",
    "UserCreate",
    "UserGet",
    # Auth
    "BasicAuthConfig",
    "GLPAuthConfig",
    # Deployments / GitLab
    "BaseDeployment",
    "GitLabConfig",
    "GitLabConfigGet",
    # Testing (test.yaml)
    "ComputorTestSuite",
    "ComputorTestCollection",
    "ComputorTest",
    "ComputorTestProperty",
    "ComputorSpecification",
    "QualificationEnum",
    "TypeEnum",
    "StatusEnum",
    "ResultEnum",
    # Testing reports
    "ComputorReport",
    "ComputorReportMain",
    "ComputorReportSub",
    "ComputorReportSummary",
    # Meta.yaml
    "CodeAbilityMeta",
    "CodeAbilityMetaProperties",
    "CodeAbilityPerson",
    "CodeAbilityLink",
    "CourseExecutionBackendConfig",
    "TestDependency",
    # Extensions
    "VsixManifestError",
    "VsixMetadata",
    "ExtensionInterface",
    "ExtensionPublishRequest",
    "ExtensionMetadata",
    "ExtensionVersionDetail",
    # Cascade Deletion
    "EntityDeleteCount",
    "CascadeDeletePreview",
    "CascadeDeleteResult",
    "ExampleDeletePreview",
    "ExampleBulkDeleteRequest",
    "ExampleBulkDeleteResult",
]
