"""
Role setup utilities for initializing system roles with claims.

This module contains functions for generating claims for system roles.
These are used during server startup to initialize the permission system.
"""

from typing import Generator, List, Tuple
from computor_types import get_all_dtos
from computor_backend.interfaces import (
    AccountInterface,
    CourseFamilyInterface,
    CourseFamilyMemberInterface,
    CourseInterface,
    OrganizationInterface,
    OrganizationMemberInterface,
    RoleClaimInterface,
    UserRoleInterface,
    UserInterface,
    StudentProfileInterface,
    ProfileInterface,
    ExtensionInterface,
)
from computor_backend.model.example import Example, ExampleRepository


def get_all_claim_values() -> Generator[Tuple[str, str], None, None]:
    """
    Get all claim values from all DTOs.
    
    Yields:
        Tuples of (claim_type, claim_value) for all registered DTOs
    """
    for dto_class in get_all_dtos():
        for claim in dto_class().claim_values():
            yield claim


def claims_user_manager() -> List[Tuple[str, str]]:
    """
    Generate claims for the user manager role.

    Returns:
        List of (claim_type, claim_value) tuples for user management permissions
    """
    claims = []

    claims.extend(UserInterface().claim_values())
    claims.extend(AccountInterface().claim_values())
    claims.extend(ProfileInterface().claim_values())
    claims.extend(StudentProfileInterface().claim_values())
    claims.extend(RoleClaimInterface().claim_values())
    claims.extend(UserRoleInterface().claim_values())

    return claims


def claims_organization_manager() -> List[Tuple[str, str]]:
    """
    Generate claims for the organization manager role.
    
    Returns:
        List of (claim_type, claim_value) tuples for organization management permissions
    """
    claims = []
    
    claims.extend(OrganizationInterface().claim_values())
    claims.extend(CourseFamilyInterface().claim_values())
    claims.extend(CourseInterface().claim_values())
    # Examples: managers may READ the example library and (via their per-course
    # roles) assign examples to courses, but authoring — uploading examples and
    # versions, editing dependencies, and deleting examples/versions/repos — is
    # reserved to the ``_example_manager`` role (see ``claims_example_manager``).
    # So grant read-only claims here, not the full CRUD ``claim_values()``.
    #
    # ExampleRepository is a distinct resource (tablename ``example_repository``)
    # behind its own CrudRouter. ExamplePermissionHandler keys general-permission
    # checks off the per-entity tablename, so the ``example:*`` claims do NOT
    # cover the example-repositories endpoints — without ``example_repository``
    # read claims managers fall through to the lecturer-in-a-course check and
    # 403 "Examples are only accessible to lecturers and above" on that page.
    claims.extend([
        ("permissions", f"{Example.__tablename__}:get"),
        ("permissions", f"{Example.__tablename__}:list"),
        ("permissions", f"{Example.__tablename__}:download"),
        ("permissions", f"{ExampleRepository.__tablename__}:get"),
        ("permissions", f"{ExampleRepository.__tablename__}:list"),
    ])
    claims.extend(ExtensionInterface().claim_values())
    # Membership tables: managers need to be able to seat / promote /
    # remove users on the orgs and families they manage. Without these
    # claims, CrudRouter's create flow finds no permitting handler and
    # falls through to the admin-only NotFoundException -> 404. Per-row
    # safety still applies via _ScopeMemberPermissionHandler — managers
    # can't grant _owner, can't touch other scopes, etc.
    claims.extend(OrganizationMemberInterface().claim_values())
    claims.extend(CourseFamilyMemberInterface().claim_values())

    return claims


def claims_example_manager() -> List[Tuple[str, str]]:
    """Generate claims for the example manager role.

    ``_example_manager`` owns the example library: uploading examples and
    example versions, editing example metadata/dependencies, and deleting
    examples, versions, and repositories. Reading examples and assigning
    them to courses is intentionally NOT exclusive to this role — a per-course
    ``_lecturer`` and ``_organization_manager`` keep read access, and
    assignment stays gated on course membership.

    The custom ``/examples`` endpoints authorize via
    ``permitted("example", <action>)`` (admin or the general ``example:*``
    claim), while the ``/example-repositories`` CrudRouter goes through
    ``ExamplePermissionHandler``, which keys general-permission checks off the
    per-entity tablename — hence both ``example`` and ``example_repository``
    claim sets are granted here.
    """
    claims: List[Tuple[str, str]] = []

    for action in ("get", "list", "download", "create", "update", "upload", "delete"):
        claims.append(("permissions", f"{Example.__tablename__}:{action}"))

    for action in ("get", "list", "create", "update", "delete"):
        claims.append(("permissions", f"{ExampleRepository.__tablename__}:{action}"))

    return claims


def claims_workspace_user() -> List[Tuple[str, str]]:
    """
    Generate claims for the workspace user role.

    Basic access: view UI, list own workspaces, start/stop own workspaces,
    view (but not manage) templates, and self-provision one workspace per
    template. Cannot provision for other users, delete, manage other users'
    workspaces, or manage templates.

    Returns:
        List of (claim_type, claim_value) tuples for workspace access permissions
    """
    return [
        ("permissions", "workspace:access"),        # Gate-keeper: can access workspace features
        ("permissions", "workspace:list"),          # List own workspaces
        ("permissions", "workspace:start"),         # Start own workspace
        ("permissions", "workspace:stop"),          # Stop own workspace
        ("permissions", "workspace:templates"),     # View templates (read-only; managing them needs workspace:manage)
        ("permissions", "workspace:provision_self"),  # Self-provision one workspace per template
    ]


def claims_workspace_maintainer() -> List[Tuple[str, str]]:
    """
    Generate claims for the workspace maintainer role.

    Full access: everything a workspace user can do, plus provisioning,
    deleting, managing other users' workspaces, and template management.

    Returns:
        List of (claim_type, claim_value) tuples for workspace maintainer permissions
    """
    return [
        # Includes all workspace user claims
        ("permissions", "workspace:access"),
        ("permissions", "workspace:list"),
        ("permissions", "workspace:start"),
        ("permissions", "workspace:stop"),
        ("permissions", "workspace:templates"),     # View templates
        ("permissions", "workspace:provision_self"),
        # Maintainer-only claims
        ("permissions", "workspace:provision"),     # Provision new workspaces (any user, custom names)
        ("permissions", "workspace:delete"),        # Delete workspaces
        ("permissions", "workspace:manage"),        # Query/manage any user's workspaces + manage templates (build/push/rollout)
        ("permissions", "workspace:session"),       # Create coder sessions
    ]


def claims_git_manager() -> List[Tuple[str, str]]:
    """
    Generate claims for the git manager role.

    Grants full access to git server user management via the /git/* endpoints.
    Works regardless of which git server backend is configured (Forgejo, GitLab, ...).
    """
    return [
        ("permissions", "git_server:manage"),
    ]
