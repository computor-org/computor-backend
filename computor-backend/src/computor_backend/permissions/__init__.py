"""
Refactored Permission System for Computor Backend

This package contains the modular, maintainable permission system that replaces
the monolithic permission checking function.

Main components:
- principal: Enhanced Principal class with structured claims
- handlers: Base permission handler interface and registry
- handlers_impl: Concrete permission handlers for each entity
- query_builders: Reusable query building components
- cache: Two-tier caching system for performance
- core: Main permission checking logic and registration
- auth: Refactored authentication with Principal creation
- migration: Tools for migrating from old to new system
"""

# Core exports for easy access
from .principal import (
    Principal,
    Claims,
    CourseRoleHierarchy,
    course_role_hierarchy,
    build_claims,
    allowed_course_role_ids,  # Backward compatibility
    build_claim_actions,  # Backward compatibility
)

from .core import (
    check_permissions,
    check_admin,
    get_permitted_course_ids,
    check_course_permissions,
    check_course_family_permissions,
    can_perform_on_resource,
    can_perform_with_parents,
    db_get_claims,
    db_get_course_claims,
    db_get_roles_claims,
    db_apply_roles,
    initialize_permission_handlers,
)

from .auth import (
    get_current_principal,
    get_current_principal,  # Backward compatibility alias
    AuthenticationService,
    PrincipalBuilder,
    get_auth_credentials,
    get_permissions_from_mockup,
)

from .cache import (
    permission_cache,
    course_permission_cache,
    cached_permission_check,
)

from .handlers import (
    PermissionHandler,
    PermissionRegistry,
    permission_registry,
)

# Migration and integration modules removed - using new system only

__all__ = [
    # Principal and Claims
    "Principal",
    "Claims",
    "CourseRoleHierarchy",
    "course_role_hierarchy",
    "build_claims",

    # Core permission functions
    "check_permissions",
    "check_admin",
    "get_permitted_course_ids",
    "check_course_permissions",
    "check_course_family_permissions",
    "can_perform_on_resource",
    "can_perform_with_parents",

    # Database functions
    "db_get_claims",
    "db_get_course_claims",
    "db_get_roles_claims",
    "db_apply_roles",

    # Authentication
    "get_current_principal",
    "get_current_principal",
    "AuthenticationService",
    "PrincipalBuilder",
    "get_auth_credentials",

    # Caching
    "permission_cache",
    "course_permission_cache",
    "cached_permission_check",

    # Handlers
    "PermissionHandler",
    "PermissionRegistry",
    "permission_registry",

    # Initialization
    "initialize_permission_handlers",
]
