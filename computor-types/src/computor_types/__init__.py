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
    import logging
    import computor_types

    logger = logging.getLogger(__name__)

    interfaces = []
    seen_names = set()
    failures: list[tuple[str, Exception]] = []

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
        except Exception as exc:
            # Do NOT silently skip: a module that fails to import here would
            # drop every EntityInterface it defines, which in the backend
            # degrades to silently-missing permissions. Record and surface.
            logger.error(
                "get_all_dtos(): failed to import %s: %s: %s",
                module_info.name, type(exc).__name__, exc, exc_info=exc,
            )
            failures.append((module_info.name, exc))

    if failures:
        # Fail loudly — permission setup depends on a complete interface list.
        names = ", ".join(name for name, _ in failures)
        raise ImportError(
            f"get_all_dtos(): {len(failures)} computor_types module(s) failed "
            f"to import and were excluded from DTO discovery: {names}. "
            "Fix the import error(s) above — a missing module silently drops "
            "its EntityInterfaces (and their backend permissions)."
        ) from failures[0][1]

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
